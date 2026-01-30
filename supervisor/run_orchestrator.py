"""Run orchestration: CALM -> VERIFY -> SKEPTICAL."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import logging
import os
from pathlib import Path
from typing import Callable, Iterable, Optional, Awaitable

from .db import ProjectionStore
from .event_publisher import EventPublisher
from .git_ops import checkpoint, git_revert, get_head_sha
from .verifier_runner import VerifierRunner, VerifierSpec
from .runtime_store import RuntimeStore
from .sandbox_runner import SandboxHandle
from .sandbox_config import build_sandbox_config
from .verifier_plan import select_verifier_plan, build_verifier_specs

logger = logging.getLogger(__name__)


class RunOrchestrator:
    def __init__(
        self,
        projection: ProjectionStore,
        publisher: EventPublisher,
        verifier_runner: Optional[VerifierRunner] = None,
        on_rollback: Optional[Callable[[str], None]] = None,
        runtime_store: Optional[RuntimeStore] = None,
    ) -> None:
        self.projection = projection
        self.publisher = publisher
        self.verifier_runner = verifier_runner or VerifierRunner()
        self.on_rollback = on_rollback
        self.runtime_store = runtime_store or RuntimeStore(user_id=projection.user_id)

    def _notify_rollback(self, run_id: str) -> None:
        if not self.on_rollback:
            return
        try:
            self.on_rollback(run_id)
        except Exception:
            pass

    def _sandbox_checkpoint_key(self) -> str:
        return f"sandbox_checkpoint:{self.projection.user_id}"

    def _get_last_sandbox_checkpoint(self) -> Optional[str]:
        return self.runtime_store.get_state(self._sandbox_checkpoint_key())

    def _create_sandbox(self, run_id: str) -> tuple[Optional[SandboxHandle], Optional[dict]]:
        try:
            config = build_sandbox_config(user_id=self.projection.user_id, workspace_id=run_id)
            handle = self.verifier_runner.sandbox_runner.create(config)
            self.verifier_runner.set_sandbox(handle)
            restore_result = None
            last_checkpoint = self._get_last_sandbox_checkpoint()
            if last_checkpoint:
                try:
                    self.verifier_runner.sandbox_runner.restore(handle, last_checkpoint)
                    restore_result = {"success": True, "checkpoint_id": last_checkpoint}
                except Exception as exc:  # pragma: no cover - defensive hook
                    restore_result = {"success": False, "checkpoint_id": last_checkpoint, "error": str(exc)}
            return handle, restore_result
        except Exception as exc:  # pragma: no cover - defensive hook
            return None, {"success": False, "error": str(exc)}

    def _destroy_sandbox(self, handle: Optional[SandboxHandle]) -> None:
        self.verifier_runner.set_sandbox(None)
        if not handle:
            return
        if os.environ.get("CHOIR_SANDBOX_KEEP", "0") == "1":
            return
        try:
            self.verifier_runner.sandbox_runner.destroy(handle)
        except Exception:
            pass

    def run(
        self,
        work_item_id: str,
        execute_run: Callable[[dict], bool],
        verifier_specs: Iterable[VerifierSpec],
        mode: str = "CALM",
    ) -> dict:
        run = self.projection.get_latest_run_for_work_item(work_item_id)
        if not run:
            raise RuntimeError(f"Run not found for work_item_id={work_item_id}")
        run_id = run["id"]
        sandbox_handle = None
        response: dict = {"run": self.projection.get_run(run_id), "verifier_results": []}

        self.publisher.publish_sync(
            "note.status",
            {"run_id": run_id, "body": {"status": "running", "mode": mode, "stage": "execute"}},
            source="agent",
        )

        try:
            sandbox_handle, restore_result = self._create_sandbox(run_id)
            if sandbox_handle:
                self.publisher.publish_sync(
                    "note.observation",
                    {"run_id": run_id, "body": {"event": "sandbox.create", "sandbox_id": sandbox_handle.sandbox_id}},
                    source="agent",
                )
                if restore_result:
                    self.publisher.publish_sync(
                        "note.observation",
                        {"run_id": run_id, "body": {"event": "sandbox.restore", "result": restore_result}},
                        source="agent",
                    )
            elif restore_result:
                self.publisher.publish_sync(
                    "note.observation",
                    {"run_id": run_id, "body": {"event": "sandbox.create", "result": restore_result}},
                    source="agent",
                )

            try:
                success = bool(execute_run(run))
            except Exception as exc:
                success = False
                self.publisher.publish_sync(
                    "note.hyperthesis",
                    {"run_id": run_id, "body": {"error": str(exc), "bound": "re-run with isolated executor"}},
                    source="agent",
                )

            if not success:
                self.publisher.publish_sync(
                    "note.status",
                    {"run_id": run_id, "body": {"status": "failed", "mode": "SKEPTICAL", "stage": "verify"}},
                    source="agent",
                )
                response = {"run": self.projection.get_run(run_id), "verifier_results": []}
                return response

            self.publisher.publish_sync(
                "note.status",
                {"run_id": run_id, "body": {"status": "verifying", "mode": mode, "stage": "verify"}},
                source="agent",
            )

            results = []
            for spec in verifier_specs:
                result = self.verifier_runner.run(spec)
                results.append(result)
                self.publisher.publish_sync(
                    "receipt.verifier.attestations",
                    {"run_id": run_id, "attestation": asdict(result)},
                    source="system",
                )

            all_passed = all(result.status == "pass" for result in results)
            final_status = "verified" if all_passed else "failed"
            self.publisher.publish_sync(
                "note.status",
                {"run_id": run_id, "body": {"status": final_status, "mode": "SKEPTICAL", "stage": "adjudicate"}},
                source="agent",
            )

            self.publisher.publish_sync(
                "receipt.verifier.attestations",
                {
                    "run_id": run_id,
                    "status": final_status,
                    "results": [asdict(r) for r in results],
                },
                source="system",
            )

            if all_passed:
                checkpoint_result = checkpoint(
                    message=f"verified checkpoint: run {run_id}",
                )
                if checkpoint_result.get("success") and checkpoint_result.get("commit_sha"):
                    self.publisher.publish_sync(
                        "checkpoint",
                        {
                            "run_id": run_id,
                            "commit_sha": checkpoint_result.get("commit_sha"),
                            "message": checkpoint_result.get("message"),
                            "mark_good": True,
                        },
                        source="system",
                    )
                self.publisher.publish_sync(
                    "note.observation",
                    {"run_id": run_id, "body": {"event": "checkpoint", "result": checkpoint_result}},
                    source="agent",
                )
                if sandbox_handle:
                    try:
                        sandbox_checkpoint = self.verifier_runner.sandbox_runner.checkpoint(
                            sandbox_handle,
                            label=f"run {run_id} verified",
                        )
                        self.runtime_store.set_state(
                            self._sandbox_checkpoint_key(),
                            sandbox_checkpoint.checkpoint_id,
                        )
                        self.publisher.publish_sync(
                            "note.observation",
                            {"run_id": run_id, "body": {"event": "sandbox.checkpoint", "result": asdict(sandbox_checkpoint)}},
                            source="agent",
                        )
                    except Exception as exc:  # pragma: no cover - defensive hook
                        self.publisher.publish_sync(
                            "note.observation",
                            {"run_id": run_id, "body": {"event": "sandbox.checkpoint", "error": str(exc)}},
                            source="agent",
                        )
                self.publisher.publish_sync(
                    "note.request.verify",
                    {
                        "run_id": run_id,
                        "body": {
                            "verifier_results": [asdict(result) for result in results],
                            "status": "ready_for_review",
                        },
                    },
                    source="agent",
                )
            else:
                last_good = self.projection.get_last_good_checkpoint()
                if not last_good:
                    last_checkpoint = self.projection.get_last_checkpoint()
                    if last_checkpoint:
                        last_good = last_checkpoint.get("commit_sha")
                if not last_good:
                    last_good = get_head_sha()
                rollback_result = None
                if last_good:
                    rollback_result = git_revert(last_good, dry_run=False)
                self.publisher.publish_sync(
                    "note.observation",
                    {"run_id": run_id, "body": {"event": "rollback", "last_good": last_good, "result": rollback_result}},
                    source="agent",
                )
                last_sandbox_checkpoint = self._get_last_sandbox_checkpoint()
                if sandbox_handle and last_sandbox_checkpoint:
                    try:
                        self.verifier_runner.sandbox_runner.restore(
                            sandbox_handle,
                            last_sandbox_checkpoint,
                        )
                        self.publisher.publish_sync(
                            "note.observation",
                            {
                                "run_id": run_id,
                                "body": {
                                    "event": "sandbox.restore",
                                    "result": {"success": True, "checkpoint_id": last_sandbox_checkpoint},
                                },
                            },
                            source="agent",
                        )
                    except Exception as exc:  # pragma: no cover - defensive hook
                        self.publisher.publish_sync(
                            "note.observation",
                            {
                                "run_id": run_id,
                                "body": {
                                    "event": "sandbox.restore",
                                    "result": {"success": False, "checkpoint_id": last_sandbox_checkpoint, "error": str(exc)},
                                },
                            },
                            source="agent",
                        )
                self._notify_rollback(run_id)

            response = {"run": self.projection.get_run(run_id), "verifier_results": results}
            return response
        finally:
            self._destroy_sandbox(sandbox_handle)

    async def run_async(
        self,
        work_item_id: str,
        execute_run: Callable[[dict], Awaitable[bool]],
        mode: str = "CALM",
        config_path: Optional[Path] = None,
    ) -> dict:
        run = self.projection.get_latest_run_for_work_item(work_item_id)
        if not run:
            raise RuntimeError(f"Run not found for work_item_id={work_item_id}")
        run_id = run["id"]
        start_seq = self.projection.get_latest_seq()
        sandbox_handle = None
        response: dict = {
            "run": self.projection.get_run(run_id),
            "verifier_plan": {},
            "verifier_results": [],
        }

        await self.publisher.publish(
            "note.status",
            {"run_id": run_id, "body": {"status": "running", "mode": mode, "stage": "execute"}},
            source="agent",
        )

        try:
            sandbox_handle, restore_result = self._create_sandbox(run_id)
            if sandbox_handle:
                await self.publisher.publish(
                    "note.observation",
                    {"run_id": run_id, "body": {"event": "sandbox.create", "sandbox_id": sandbox_handle.sandbox_id}},
                    source="agent",
                )
                if restore_result:
                    await self.publisher.publish(
                        "note.observation",
                        {"run_id": run_id, "body": {"event": "sandbox.restore", "result": restore_result}},
                        source="agent",
                    )
            elif restore_result:
                await self.publisher.publish(
                    "note.observation",
                    {"run_id": run_id, "body": {"event": "sandbox.create", "result": restore_result}},
                    source="agent",
                )

            try:
                success = bool(await execute_run(run))
            except Exception as exc:
                success = False
                await self.publisher.publish(
                    "note.hyperthesis",
                    {"run_id": run_id, "body": {"error": str(exc), "bound": "re-run with isolated executor"}},
                    source="agent",
                )

            touched_paths = self.projection.get_event_paths_since(start_seq)
            work_item = self.projection.get_work_item(work_item_id) or {}
            required_verifiers = work_item.get("required_verifiers", [])
            risk_tier = work_item.get("risk_tier")

            # BAML-powered task assessment
            baml_assessment = None
            prompt = work_item.get("prompt", "")
            if prompt:
                try:
                    from .baml_client import b
                    from .provider_factory import get_provider_factory

                    factory = get_provider_factory(self.projection)
                    client = factory.get_baml_client()
                    baml_assessment = await b.with_options(client=client).AssessTask(prompt=prompt)
                    await self.publisher.publish(
                        "note.observation",
                        {
                            "run_id": run_id,
                            "body": {
                                "event": "baml.assessment",
                                "complexity": baml_assessment.complexity,
                                "requires_verification": baml_assessment.requires_verification,
                                "risk_factors": baml_assessment.risk_factors,
                                "estimated_steps": baml_assessment.estimated_steps,
                            },
                        },
                        source="agent",
                    )
                    # Override risk_tier if BAML suggests verification not needed
                    if baml_assessment.complexity == "TRIVIAL" and not baml_assessment.requires_verification:
                        if not risk_tier:
                            risk_tier = "low"
                            logger.info(f"BAML assessment: TRIVIAL task, setting risk_tier=low")
                except Exception as exc:
                    logger.warning(f"BAML assessment failed: {exc}")
                    await self.publisher.publish(
                        "note.observation",
                        {"run_id": run_id, "body": {"event": "baml.assessment", "error": str(exc)}},
                        source="agent",
                    )

            plan = select_verifier_plan(
                touched_paths=touched_paths,
                mode=mode,
                required_verifiers=required_verifiers,
                risk_tier=risk_tier,
                config_path=config_path,
            )
            verifier_specs = build_verifier_specs(plan.verifier_ids, config_path=config_path)

            if not success:
                await self.publisher.publish(
                    "note.status",
                    {"run_id": run_id, "body": {"status": "failed", "mode": "SKEPTICAL", "stage": "verify"}},
                    source="agent",
                )
                response = {
                    "run": self.projection.get_run(run_id),
                    "verifier_plan": plan.to_dict(),
                    "verifier_results": [],
                }
                return response

            await self.publisher.publish(
                "note.status",
                {"run_id": run_id, "body": {"status": "verifying", "mode": mode, "stage": "verify"}},
                source="agent",
            )

            results = []
            for spec in verifier_specs:
                result = await self.verifier_runner.run_async(spec)
                results.append(result)
                await self.publisher.publish(
                    "receipt.verifier.attestations",
                    {"run_id": run_id, "attestation": asdict(result)},
                    source="system",
                )

            all_passed = all(result.status == "pass" for result in results)
            final_status = "verified" if all_passed else "failed"
            await self.publisher.publish(
                "note.status",
                {"run_id": run_id, "body": {"status": final_status, "mode": "SKEPTICAL", "stage": "adjudicate"}},
                source="agent",
            )

            await self.publisher.publish(
                "receipt.verifier.attestations",
                {
                    "run_id": run_id,
                    "status": final_status,
                    "results": [asdict(r) for r in results],
                },
                source="system",
            )

            if all_passed:
                checkpoint_result = checkpoint(
                    message=f"verified checkpoint: run {run_id}",
                )
                if checkpoint_result.get("success") and checkpoint_result.get("commit_sha"):
                    await self.publisher.publish(
                        "checkpoint",
                        {
                            "run_id": run_id,
                            "commit_sha": checkpoint_result.get("commit_sha"),
                            "message": checkpoint_result.get("message"),
                            "mark_good": True,
                        },
                        source="system",
                    )
                await self.publisher.publish(
                    "note.observation",
                    {"run_id": run_id, "body": {"event": "checkpoint", "result": checkpoint_result}},
                    source="agent",
                )
                if sandbox_handle:
                    try:
                        sandbox_checkpoint = self.verifier_runner.sandbox_runner.checkpoint(
                            sandbox_handle,
                            label=f"run {run_id} verified",
                        )
                        self.runtime_store.set_state(
                            self._sandbox_checkpoint_key(),
                            sandbox_checkpoint.checkpoint_id,
                        )
                        await self.publisher.publish(
                            "note.observation",
                            {"run_id": run_id, "body": {"event": "sandbox.checkpoint", "result": asdict(sandbox_checkpoint)}},
                            source="agent",
                        )
                    except Exception as exc:  # pragma: no cover - defensive hook
                        await self.publisher.publish(
                            "note.observation",
                            {"run_id": run_id, "body": {"event": "sandbox.checkpoint", "error": str(exc)}},
                            source="agent",
                        )
                await self.publisher.publish(
                    "note.request.verify",
                    {
                        "run_id": run_id,
                        "body": {
                            "verifier_plan": plan.to_dict(),
                            "verifier_results": [asdict(result) for result in results],
                            "status": "ready_for_review",
                        },
                    },
                    source="agent",
                )
            else:
                last_good = self.projection.get_last_good_checkpoint()
                if not last_good:
                    last_checkpoint = self.projection.get_last_checkpoint()
                    if last_checkpoint:
                        last_good = last_checkpoint.get("commit_sha")
                if not last_good:
                    last_good = get_head_sha()
                rollback_result = None
                if last_good:
                    rollback_result = git_revert(last_good, dry_run=False)
                await self.publisher.publish(
                    "note.observation",
                    {"run_id": run_id, "body": {"event": "rollback", "last_good": last_good, "result": rollback_result}},
                    source="agent",
                )
                last_sandbox_checkpoint = self._get_last_sandbox_checkpoint()
                if sandbox_handle and last_sandbox_checkpoint:
                    try:
                        self.verifier_runner.sandbox_runner.restore(
                            sandbox_handle,
                            last_sandbox_checkpoint,
                        )
                        await self.publisher.publish(
                            "note.observation",
                            {
                                "run_id": run_id,
                                "body": {
                                    "event": "sandbox.restore",
                                    "result": {"success": True, "checkpoint_id": last_sandbox_checkpoint},
                                },
                            },
                            source="agent",
                        )
                    except Exception as exc:  # pragma: no cover - defensive hook
                        await self.publisher.publish(
                            "note.observation",
                            {
                                "run_id": run_id,
                                "body": {
                                    "event": "sandbox.restore",
                                    "result": {"success": False, "checkpoint_id": last_sandbox_checkpoint, "error": str(exc)},
                                },
                            },
                            source="agent",
                        )
                self._notify_rollback(run_id)

            response = {
                "run": self.projection.get_run(run_id),
                "verifier_plan": plan.to_dict(),
                "verifier_results": results,
            }
            return response
        finally:
            self._destroy_sandbox(sandbox_handle)
