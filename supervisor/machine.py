"""Machine control plane for mode orchestration."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable, Optional, Any

import nats
from nats.js.api import ConsumerConfig

from .db import EventStore
from .event_contract import build_subject
from .mode_config import ModeConfig, get_mode_config
from .mode_engine import ModeInputs, select_initial_mode
from .nats_client import ChoirEvent, NATS_MSG_ID_HEADER
from .nats_metrics import NATS_METRICS


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

logger = logging.getLogger("machine.nats")

DIRECTIVE_CONSUMER_PREFIX = "mode-start"
DIRECTIVE_ACK_WAIT_SECONDS = 30
DIRECTIVE_MAX_DELIVER = 5
DIRECTIVE_BACKOFF_SECONDS = [1, 5, 30]
DIRECTIVE_FETCH_BATCH = 10
DIRECTIVE_FETCH_TIMEOUT = 1.0


@dataclass(frozen=True)
class NatsDeliveryContext:
    stream: Optional[str]
    consumer: str
    subject: str
    sequence: Optional[int]
    delivery_count: int


class Machine:
    def __init__(self, store: EventStore, executor: ModeExecutor, session_id: Optional[str] = None) -> None:
        self.store = store
        self.executor = executor
        self.session_id = session_id
        self._writer_lock = asyncio.Lock()
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._nats_task: Optional[asyncio.Task] = None
        self._nats_metrics = NATS_METRICS
        self._listening = False

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
        await self.stop_listening()

    async def stop_listening(self) -> None:
        self._listening = False
        if self._nats_task:
            self._nats_task.cancel()
            try:
                await self._nats_task
            except asyncio.CancelledError:
                pass
            self._nats_task = None

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
            durable = f"{DIRECTIVE_CONSUMER_PREFIX}.{self.store.user_id}"
            config = ConsumerConfig(
                ack_policy="explicit",
                ack_wait=DIRECTIVE_ACK_WAIT_SECONDS * 1_000_000_000,
                max_deliver=DIRECTIVE_MAX_DELIVER,
                backoff=[delay * 1_000_000_000 for delay in DIRECTIVE_BACKOFF_SECONDS],
                deliver_policy="new",
            )
            subscription = await nats.pull_subscribe(subject, durable=durable, config=config)
            self._listening = True
            self._nats_task = asyncio.create_task(
                self._directive_consumer_loop(subscription, durable)
            )
            return True
        except Exception:
            return False

    async def _directive_consumer_loop(self, subscription, consumer: str) -> None:
        while self._listening:
            try:
                msgs = await subscription.fetch(DIRECTIVE_FETCH_BATCH, timeout=DIRECTIVE_FETCH_TIMEOUT)
            except nats.errors.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("directive consumer error: %s", exc)
                await asyncio.sleep(1)
                continue

            for msg in msgs:
                await self._handle_directive_message(msg, consumer)

    async def _handle_directive_message(self, msg, consumer: str) -> None:
        started = time.monotonic()
        event = ChoirEvent.from_json(msg.data)
        metadata = msg.metadata
        sequence = metadata.sequence.stream if metadata else None
        delivery_count = metadata.num_delivered if metadata else 1
        context = NatsDeliveryContext(
            stream=metadata.stream if metadata else None,
            consumer=consumer,
            subject=msg.subject,
            sequence=sequence,
            delivery_count=delivery_count,
        )
        event_id = event.id
        if not event_id and msg.headers:
            event_id = msg.headers.get(NATS_MSG_ID_HEADER)
        if not event_id and sequence is not None:
            event_id = f"nats:{sequence}"

        if not event_id:
            await msg.ack()
            return

        is_new, status = self.store.record_event_delivery(
            consumer=consumer,
            event_id=event_id,
            nats_seq=sequence,
            subject=msg.subject,
            delivery_count=delivery_count,
        )
        dedupe_hit = (not is_new) and status == "done"
        self._nats_metrics.record_delivery(delivery_count)
        self._nats_metrics.record_dedupe(dedupe_hit)

        if dedupe_hit:
            latency_ms = (time.monotonic() - started) * 1000
            await msg.ack()
            self._nats_metrics.record_ack(latency_ms)
            self._log_delivery(context, event_id, "ack", "dedupe", latency_ms)
            return

        try:
            self.store.mark_event_processing(consumer, event_id)
            await self.handle_event(event)
            self.store.mark_event_done(consumer, event_id)
            latency_ms = (time.monotonic() - started) * 1000
            await msg.ack()
            self._nats_metrics.record_ack(latency_ms)
            self._nats_metrics.record_handler_latency(latency_ms)
            self._log_delivery(context, event_id, "ack", "processed", latency_ms)
        except Exception as exc:
            self.store.mark_event_failed(consumer, event_id, str(exc))
            if delivery_count >= DIRECTIVE_MAX_DELIVER:
                await self._publish_dlq(event, context, str(exc))
                latency_ms = (time.monotonic() - started) * 1000
                await msg.ack()
                self._nats_metrics.record_dlq()
                self._nats_metrics.record_ack(latency_ms)
                self._log_delivery(context, event_id, "ack", "dlq", latency_ms)
            else:
                await msg.nak()
                self._nats_metrics.record_nak()
                self._log_delivery(context, event_id, "nak", "retry", (time.monotonic() - started) * 1000)

    async def _publish_dlq(self, event: ChoirEvent, context: NatsDeliveryContext, error: str) -> None:
        from .nats_client import get_nats_client

        nats = await get_nats_client()
        payload = {
            "event": event.to_dict(),
            "error": error,
            "stream": context.stream,
            "consumer": context.consumer,
            "subject": context.subject,
            "sequence": context.sequence,
            "delivery_count": context.delivery_count,
        }
        dlq_event = ChoirEvent(
            id=event.id,
            timestamp=int(datetime.now().timestamp() * 1000),
            user_id=event.user_id,
            source="system",
            event_type="receipt.dlq",
            payload=payload,
        )
        await nats.publish_event(dlq_event)

    def _log_delivery(
        self,
        context: NatsDeliveryContext,
        event_id: str,
        ack: str,
        outcome: str,
        latency_ms: float,
    ) -> None:
        logger.info(
            json.dumps(
                {
                    "stream": context.stream,
                    "consumer": context.consumer,
                    "subject": context.subject,
                    "sequence": context.sequence,
                    "delivery_count": context.delivery_count,
                    "ack": ack,
                    "outcome": outcome,
                    "event_id": event_id,
                    "latency_ms": latency_ms,
                }
            )
        )

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
