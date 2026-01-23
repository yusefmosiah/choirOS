"""Machine control plane for mode orchestration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional, Any

from .db import EventStore
from .event_contract import build_subject
from .mode_config import ModeConfig, get_mode_config


@dataclass(frozen=True)
class ModeDirective:
    mode_id: str
    prompt: str
    work_item_id: str
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

    def _select_mode(self, prompt: str) -> ModeConfig:
        # TODO: Replace with AHDB-driven selection + guards.
        return get_mode_config("CALM")

    async def handle_prompt(self, prompt: str, requested_mode: Optional[str] = None) -> ModeRunResult:
        mode_config = get_mode_config(requested_mode) if requested_mode else self._select_mode(prompt)
        work_item = self.store.create_work_item(description=prompt, status="queued")
        directive = ModeDirective(
            mode_id=mode_config.mode_id,
            prompt=prompt,
            work_item_id=work_item["id"],
            allow_write=mode_config.allow_write,
            session_id=self.session_id,
        )
        if directive.allow_write:
            async with self._writer_lock:
                return await self._run_directive(directive, emit_start=True)
        return await self._run_directive(directive, emit_start=True)

    async def handle_event(self, event: Any) -> None:
        if event.event_type != "mode.start":
            return
        payload = event.payload or {}
        session_id = payload.get("session_id")
        if self.session_id and session_id and session_id != self.session_id:
            return
        mode_id = payload.get("mode") or payload.get("mood") or "CALM"
        prompt = payload.get("prompt") or ""
        work_item_id = payload.get("work_item_id")
        if not work_item_id:
            work_item = self.store.create_work_item(description=prompt, status="queued")
            work_item_id = work_item["id"]
        mode_config = get_mode_config(mode_id)
        directive = ModeDirective(
            mode_id=mode_config.mode_id,
            prompt=prompt,
            work_item_id=work_item_id,
            allow_write=payload.get("allow_write", mode_config.allow_write),
            session_id=session_id,
        )
        if directive.allow_write:
            async with self._writer_lock:
                await self._run_directive(directive, emit_start=False)
        else:
            await self._run_directive(directive, emit_start=False)

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
                    "allow_write": directive.allow_write,
                    "prompt": directive.prompt,
                    "session_id": directive.session_id,
                },
                source="system",
            )
        result = await self.executor(directive)
        if result.run_id:
            self.store.append(
                "mode.update",
                {
                    "mode": directive.mode_id,
                    "run_id": result.run_id,
                    "status": result.status,
                },
                source="system",
            )
        self.store.append(
            "mode.stop",
            {
                "mode": directive.mode_id,
                "run_id": result.run_id,
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
            self.store.log_ahdb_delta(
                delta,
                {
                    "run_id": run_id,
                    "authority": "asserted",
                    "evidence_event_seq": proposal.get("event_seq"),
                },
            )
            promoted += 1
        if promoted:
            self.store.mark_ahdb_proposals_promoted(run_id)
        return promoted
