"""Machine control plane for mode orchestration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable, Optional, Any

from .db import EventStore
from .event_contract import build_subject
from .mode_config import ModeConfig, get_mode_config
from .mode_engine import ModeInputs, select_initial_mode


@dataclass(frozen=True)
class ModeDirective:
    mode_id: str
    prompt: str
    work_item_id: str
    run_id: str
    allow_write: bool
    session_id: Optional[str] = None


@dataclass(frozen=True)
class ModeRunResult:
    run_id: Optional[str]
    status: str
    verifier_results: list[dict]


ModeExecutor = Callable[[ModeDirective], Awaitable[ModeRunResult]]


class Machine:
    def __init__(self, store: EventStore, executor: ModeExecutor, session_id: Optional[str] = None) -> None:
        self.store = store
        self.executor = executor
        self.session_id = session_id
        self._writer_lock = asyncio.Lock()
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None

    def start_loop(self):
        if self._running:
            return
        self._running = True
        self._loop_task = asyncio.create_task(self._scheduler_loop())

    async def stop_loop(self):
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            self._loop_task = None

    async def _scheduler_loop(self):
        while self._running:
            try:
                # Acquire lock for entire claim-execute cycle to ensure serialization
                async with self._writer_lock:
                    # 1. Atomically claim queued work (FIFO by created_at)
                    runner_id = self.session_id or "machine"
                    item = self.store.claim_next_work_item(runner_id)
                    if not item:
                        # Release lock briefly before sleeping
                        pass
                    else:
                        work_item_id = item["id"]
                        prompt = item["description"]
                        run = self.store.get_or_create_run_for_work_item(work_item_id)
                        if not run:
                            await asyncio.sleep(0.1)
                            continue
                        run_id = run["id"]
                        existing_inputs = self.store.list_run_inputs(run_id, limit=1)
                        if not existing_inputs:
                            self.store.add_run_input(run_id, prompt, kind="initial")

                        # 2. Determine mode (TODO: AHDB selector)
                        mode_config = self._select_mode(prompt)

                        directive = ModeDirective(
                            mode_id=mode_config.mode_id,
                            prompt=prompt,
                            work_item_id=work_item_id,
                            run_id=run_id,
                            allow_write=mode_config.allow_write,
                            session_id=self.session_id,
                        )

                        # 3. Mark as running, execute, then mark completed
                        try:
                            started_at = datetime.now().isoformat()
                            self.store.update_run(
                                run_id,
                                {"status": "running", "started_at": started_at},
                            )
                            await self._run_directive(directive, emit_start=True)
                            self.store.update_work_item(work_item_id, {"status": "completed"})
                            finished_at = datetime.now().isoformat()
                            self.store.update_run(run_id, {"status": "completed", "finished_at": finished_at})
                        except Exception as exec_err:
                            self.store.update_work_item(work_item_id, {"status": "failed"})
                            failed_at = datetime.now().isoformat()
                            self.store.update_run(run_id, {"status": "failed", "finished_at": failed_at})
                            raise exec_err
                        continue  # Check for more work immediately

                await asyncio.sleep(0.1)  # Brief sleep when no work

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in machine scheduler loop: {e}")
                await asyncio.sleep(5)

    def _select_mode(self, prompt: str) -> ModeConfig:
        """Select mode based on AHDB state vector."""
        ahdb = self.store.get_ahdb_state()
        
        # Map AHDB state to ModeInputs
        # AHDB keys: crash_detected, has_demo, conjectures, repeated_failures, etc.
        inputs = ModeInputs(
            crash_detected=ahdb.get("crash_detected", False),
            has_demo=ahdb.get("has_demo", True),
            conjectures_present=bool(ahdb.get("conjectures", [])),
            repeated_verifier_failures=ahdb.get("repeated_verifier_failures", False),
            about_to_cross_privilege_boundary=ahdb.get("privilege_boundary", False),
            preference_missing=ahdb.get("preference_missing", False),
            ambiguity_blocking=ahdb.get("ambiguity_blocking", False),
            user_idk=ahdb.get("user_idk", False),
            verifiers_regress=ahdb.get("verifiers_regress", False),
            hyperthesis_high=ahdb.get("hyperthesis_high", False),
            mitigations_installed=ahdb.get("mitigations_installed", False),
            verified_and_bounded=ahdb.get("verified_and_bounded", False),
            suspected_reward_hack=ahdb.get("suspected_reward_hack", False),
            state_consistent=ahdb.get("state_consistent", True),
            previous_mode=ahdb.get("previous_mode"),
        )
        
        mode_id = select_initial_mode(inputs)
        return get_mode_config(mode_id)

    async def handle_prompt(self, prompt: str, requested_mode: Optional[str] = None) -> str:
        """Enqueue a prompt for execution. Returns work_item_id."""
        work_item = self.store.create_work_item(description=prompt, status="queued")
        return work_item["id"]

    async def handle_event(self, event: Any) -> None:
        if event.event_type != "mode.start":
            return
        payload = event.payload or {}
        session_id = payload.get("session_id")
        if self.session_id and session_id and session_id != self.session_id:
            return
        prompt = payload.get("prompt") or ""
        work_item_id = payload.get("work_item_id")
        if not work_item_id:
            self.store.create_work_item(description=prompt, status="queued")
            return
        existing = self.store.get_work_item(work_item_id)
        if existing is None:
            self.store.create_work_item(description=prompt, status="queued")
            return
        if existing.get("status") not in {"running"}:
            self.store.update_work_item(work_item_id, {"status": "queued"})
        run = self.store.get_or_create_run_for_work_item(work_item_id)
        if run and run.get("status") not in {"running"}:
            self.store.update_run(run["id"], {"status": "queued"})

    async def listen_for_directives(self) -> bool:
        try:
            from .nats_client import get_nats_client

            nats = await get_nats_client()
            subject = build_subject(self.store.user_id, "system", "mode.start")
            await nats.subscribe(subject, self.handle_event)
            return True
        except Exception:
            return False

    async def _run_directive(self, directive: ModeDirective, emit_start: bool) -> ModeRunResult:
        if emit_start:
            self.store.append(
                "mode.start",
                {
                    "mode": directive.mode_id,
                    "work_item_id": directive.work_item_id,
                    "run_id": directive.run_id,
                    "allow_write": directive.allow_write,
                    "prompt": directive.prompt,
                    "session_id": directive.session_id,
                },
                source="system",
            )
        result = await self.executor(directive)
        self.store.append(
            "mode.update",
            {
                "mode": directive.mode_id,
                "run_id": directive.run_id,
                "orchestrator_run_id": result.run_id,
                "status": result.status,
            },
            source="system",
        )
        self.store.append(
            "mode.stop",
            {
                "mode": directive.mode_id,
                "run_id": directive.run_id,
                "orchestrator_run_id": result.run_id,
                "status": result.status,
                "session_id": directive.session_id,
            },
            source="system",
        )
        return result

    def promote_ahdb_proposals(self, run_id: str) -> int:
        run = self.store.get_run(run_id)
        if not run or run.get("status") != "verified":
            return 0

        proposals = self.store.list_ahdb_proposals(run_id)
        promoted = 0
        for proposal in proposals:
            if proposal.get("status") != "proposed":
                continue
            delta = proposal.get("delta")
            if not delta:
                continue
            self.store.log_ahdb_delta(delta, {"run_id": run_id, "authority": "asserted", "evidence_run_id": run_id})
            promoted += 1
        if promoted:
            self.store.mark_ahdb_proposals_promoted(run_id)
        return promoted
