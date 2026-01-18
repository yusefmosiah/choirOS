"""Run orchestration: CALM -> VERIFY -> SKEPTICAL."""

from __future__ import annotations

from dataclasses import asdict
import os
from pathlib import Path
from typing import Callable, Iterable, Optional, Awaitable

from .db import EventStore
from .git_ops import checkpoint, git_revert, get_head_sha
from .verifier_runner import VerifierRunner, VerifierSpec
from .sandbox_runner import SandboxHandle
from .sandbox_config import build_sandbox_config
from .verifier_plan import select_verifier_plan, build_verifier_specs


class RunOrchestrator:
    def __init__(
        self,
        store: EventStore,
        verifier_runner: Optional[VerifierRunner] = None,
        on_rollback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.store = store
        self.verifier_runner = verifier_runner or VerifierRunner()
        self.on_rollback = on_rollback

    def _notify_rollback(self, run_id: str) -> None:
        if not self.on_rollback:
            return
        try:
            self.on_rollback(run_id)
        except Exception:
            pass

    def _ensure_last_good_checkpoint(self) -> None:
        if self.store.get_last_good_checkpoint():
            return
        head = get_head_sha()
        if head:
            self.store.set_last_good_checkpoint(head)

    def _sandbox_checkpoint_key(self) -> str:
        return f"sandbox_checkpoint:{self.store.user_id}"

    def _get_last_sandbox_checkpoint(self) -> Optional[str]:
        return self.store.get_sync_state(self._sandbox_checkpoint_key())

    def _set_last_sandbox_checkpoint(self, checkpoint_id: str) -> None:
        if checkpoint_id:
            self.store.set_sync_state(self._sandbox_checkpoint_key(), checkpoint_id)

    def _create_sandbox(self, run_id: str) -> tuple[Optional[SandboxHandle], Optional[dict]]:
        try:
            config = build_sandbox_config(user_id=self.store.user_id, workspace_id=run_id)
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
        mood: str = "CALM",
    ) -> dict:
        run = self.store.create_run(work_item_id=work_item_id, mood=mood, status="running")
        run_id = run["id"]
        self._ensure_last_good_checkpoint()
        sandbox_handle = None
        response: dict = {"run": self.store.get_run(run_id), "verifier_results": []}

        self.store.add_run_note(
            run_id,
            "note.status",
            {"status": "running", "mood": mood, "stage": "execute"},
        )

        try:
            sandbox_handle, restore_result = self._create_sandbox(run_id)
            if sandbox_handle:
                self.store.add_run_note(
                    run_id,
                    "note.observation",
                    {"event": "sandbox.create", "sandbox_id": sandbox_handle.sandbox_id},
                )
                if restore_result:
                    self.store.add_run_note(
                        run_id,
                        "note.observation",
                        {"event": "sandbox.restore", "result": restore_result},
                    )
            elif restore_result:
                self.store.add_run_note(
                    run_id,
                    "note.observation",
                    {"event": "sandbox.create", "result": restore_result},
                )

            try:
                success = bool(execute_run(run))
            except Exception as exc:
                success = False
                self.store.add_run_note(
                    run_id,
                    "note.hyperthesis",
                    {"error": str(exc), "bound": "re-run with isolated executor"},
                )

            if not success:
                self.store.update_run(run_id, {"status": "failed", "mood": "SKEPTICAL"})
                self.store.add_run_note(
                    run_id,
                    "note.status",
                    {"status": "failed", "mood": "SKEPTICAL", "stage": "verify"},
                )
                response = {"run": self.store.get_run(run_id), "verifier_results": []}
                return response

            self.store.update_run(run_id, {"status": "verifying"})
            self.store.add_run_note(
                run_id,
                "note.status",
                {"status": "verifying", "mood": mood, "stage": "verify"},
            )

            results = []
            for spec in verifier_specs:
                result = self.verifier_runner.run(spec)
                results.append(result)
                self.store.add_run_verification(run_id, asdict(result))

            all_passed = all(result.status == "pass" for result in results)
            final_status = "verified" if all_passed else "failed"
            self.store.update_run(run_id, {"status": final_status, "mood": "SKEPTICAL"})
            self.store.add_run_note(
                run_id,
                "note.status",
                {"status": final_status, "mood": "SKEPTICAL", "stage": "adjudicate"},
            )

            if all_passed:
                checkpoint_result = checkpoint(
                    message=f"verified checkpoint: run {run_id}",
                    store=self.store,
                )
                if checkpoint_result.get("success") and checkpoint_result.get("commit_sha"):
                    self.store.set_last_good_checkpoint(checkpoint_result["commit_sha"])
                self.store.add_run_note(
                    run_id,
                    "note.observation",
                    {"event": "checkpoint", "result": checkpoint_result},
                )
                if sandbox_handle:
                    try:
                        sandbox_checkpoint = self.verifier_runner.sandbox_runner.checkpoint(
                            sandbox_handle,
                            label=f"run {run_id} verified",
                        )
                        self._set_last_sandbox_checkpoint(sandbox_checkpoint.checkpoint_id)
                        self.store.add_run_note(
                            run_id,
                            "note.observation",
                            {"event": "sandbox.checkpoint", "result": asdict(sandbox_checkpoint)},
                        )
                    except Exception as exc:  # pragma: no cover - defensive hook
                        self.store.add_run_note(
                            run_id,
                            "note.observation",
                            {"event": "sandbox.checkpoint", "error": str(exc)},
                        )
                self.store.add_commit_request(
                    run_id,
                    {
                        "verifier_results": [asdict(result) for result in results],
                        "status": "ready_for_review",
                    },
                )
            else:
                last_good = self.store.get_last_good_checkpoint()
                rollback_result = None
                if last_good:
                    rollback_result = git_revert(last_good, dry_run=False)
                self.store.add_run_note(
                    run_id,
                    "note.observation",
                    {"event": "rollback", "last_good": last_good, "result": rollback_result},
                )
                last_sandbox_checkpoint = self._get_last_sandbox_checkpoint()
                if sandbox_handle and last_sandbox_checkpoint:
                    try:
                        self.verifier_runner.sandbox_runner.restore(
                            sandbox_handle,
                            last_sandbox_checkpoint,
                        )
                        self.store.add_run_note(
                            run_id,
                            "note.observation",
                            {
                                "event": "sandbox.restore",
                                "result": {"success": True, "checkpoint_id": last_sandbox_checkpoint},
                            },
                        )
                    except Exception as exc:  # pragma: no cover - defensive hook
                        self.store.add_run_note(
                            run_id,
                            "note.observation",
                            {
                                "event": "sandbox.restore",
                                "result": {"success": False, "checkpoint_id": last_sandbox_checkpoint, "error": str(exc)},
                            },
                        )
                self._notify_rollback(run_id)

            response = {"run": self.store.get_run(run_id), "verifier_results": results}
            return response
        finally:
            self._destroy_sandbox(sandbox_handle)

    async def run_async(
        self,
        work_item_id: str,
        execute_run: Callable[[dict], Awaitable[bool]],
        mood: str = "CALM",
        config_path: Optional[Path] = None,
    ) -> dict:
        run = self.store.create_run(work_item_id=work_item_id, mood=mood, status="running")
        run_id = run["id"]
        start_seq = self.store.get_latest_seq()
        self._ensure_last_good_checkpoint()
        sandbox_handle = None
        response: dict = {
            "run": self.store.get_run(run_id),
            "verifier_plan": {},
            "verifier_results": [],
        }

        self.store.add_run_note(
            run_id,
            "note.status",
            {"status": "running", "mood": mood, "stage": "execute"},
        )

        try:
            sandbox_handle, restore_result = self._create_sandbox(run_id)
            if sandbox_handle:
                self.store.add_run_note(
                    run_id,
                    "note.observation",
                    {"event": "sandbox.create", "sandbox_id": sandbox_handle.sandbox_id},
                )
                if restore_result:
                    self.store.add_run_note(
                        run_id,
                        "note.observation",
                        {"event": "sandbox.restore", "result": restore_result},
                    )
            elif restore_result:
                self.store.add_run_note(
                    run_id,
                    "note.observation",
                    {"event": "sandbox.create", "result": restore_result},
                )

            try:
                success = bool(await execute_run(run))
            except Exception as exc:
                success = False
                self.store.add_run_note(
                    run_id,
                    "note.hyperthesis",
                    {"error": str(exc), "bound": "re-run with isolated executor"},
                )

            touched_paths = self.store.get_event_paths_since(start_seq)
            work_item = self.store.get_work_item(work_item_id) or {}
            required_verifiers = work_item.get("required_verifiers", [])
            risk_tier = work_item.get("risk_tier")

            plan = select_verifier_plan(
                touched_paths=touched_paths,
                mood=mood,
                required_verifiers=required_verifiers,
                risk_tier=risk_tier,
                config_path=config_path,
            )
            verifier_specs = build_verifier_specs(plan.verifier_ids, config_path=config_path)

            if not success:
                self.store.update_run(run_id, {"status": "failed", "mood": "SKEPTICAL"})
                self.store.add_run_note(
                    run_id,
                    "note.status",
                    {"status": "failed", "mood": "SKEPTICAL", "stage": "verify"},
                )
                response = {
                    "run": self.store.get_run(run_id),
                    "verifier_plan": plan.to_dict(),
                    "verifier_results": [],
                }
                return response

            self.store.update_run(run_id, {"status": "verifying"})
            self.store.add_run_note(
                run_id,
                "note.status",
                {"status": "verifying", "mood": mood, "stage": "verify"},
            )

            results = []
            for spec in verifier_specs:
                result = self.verifier_runner.run(spec)
                results.append(result)
                self.store.add_run_verification(run_id, asdict(result))

            all_passed = all(result.status == "pass" for result in results)
            final_status = "verified" if all_passed else "failed"
            self.store.update_run(run_id, {"status": final_status, "mood": "SKEPTICAL"})
            self.store.add_run_note(
                run_id,
                "note.status",
                {"status": final_status, "mood": "SKEPTICAL", "stage": "adjudicate"},
            )

            if all_passed:
                checkpoint_result = checkpoint(
                    message=f"verified checkpoint: run {run_id}",
                    store=self.store,
                )
                if checkpoint_result.get("success") and checkpoint_result.get("commit_sha"):
                    self.store.set_last_good_checkpoint(checkpoint_result["commit_sha"])
                self.store.add_run_note(
                    run_id,
                    "note.observation",
                    {"event": "checkpoint", "result": checkpoint_result},
                )
                if sandbox_handle:
                    try:
                        sandbox_checkpoint = self.verifier_runner.sandbox_runner.checkpoint(
                            sandbox_handle,
                            label=f"run {run_id} verified",
                        )
                        self._set_last_sandbox_checkpoint(sandbox_checkpoint.checkpoint_id)
                        self.store.add_run_note(
                            run_id,
                            "note.observation",
                            {"event": "sandbox.checkpoint", "result": asdict(sandbox_checkpoint)},
                        )
                    except Exception as exc:  # pragma: no cover - defensive hook
                        self.store.add_run_note(
                            run_id,
                            "note.observation",
                            {"event": "sandbox.checkpoint", "error": str(exc)},
                        )
                self.store.add_commit_request(
                    run_id,
                    {
                        "verifier_plan": plan.to_dict(),
                        "verifier_results": [asdict(result) for result in results],
                        "status": "ready_for_review",
                    },
                )
            else:
                last_good = self.store.get_last_good_checkpoint()
                rollback_result = None
                if last_good:
                    rollback_result = git_revert(last_good, dry_run=False)
                self.store.add_run_note(
                    run_id,
                    "note.observation",
                    {"event": "rollback", "last_good": last_good, "result": rollback_result},
                )
                last_sandbox_checkpoint = self._get_last_sandbox_checkpoint()
                if sandbox_handle and last_sandbox_checkpoint:
                    try:
                        self.verifier_runner.sandbox_runner.restore(
                            sandbox_handle,
                            last_sandbox_checkpoint,
                        )
                        self.store.add_run_note(
                            run_id,
                            "note.observation",
                            {
                                "event": "sandbox.restore",
                                "result": {"success": True, "checkpoint_id": last_sandbox_checkpoint},
                            },
                        )
                    except Exception as exc:  # pragma: no cover - defensive hook
                        self.store.add_run_note(
                            run_id,
                            "note.observation",
                            {
                                "event": "sandbox.restore",
                                "result": {"success": False, "checkpoint_id": last_sandbox_checkpoint, "error": str(exc)},
                            },
                        )
                self._notify_rollback(run_id)

            response = {
                "run": self.store.get_run(run_id),
                "verifier_plan": plan.to_dict(),
                "verifier_results": results,
            }
            return response
        finally:
            self._destroy_sandbox(sandbox_handle)
