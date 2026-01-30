"""Machine control plane for mode orchestration."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable, Optional, Any

import nats
from nats.js.api import ConsumerConfig

from .db import ProjectionStore
from .event_contract import build_subject
from .event_publisher import EventPublisher
from .mode_config import ModeConfig, get_mode_config
from .mode_engine import ModeInputs, select_initial_mode
from .nats_client import ChoirEvent, NATS_MSG_ID_HEADER
from .nats_metrics import NATS_METRICS
from .runtime_store import RuntimeStore


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

INPUT_CONSUMER_PREFIX = "run-input"
INPUT_ACK_WAIT_SECONDS = 30
INPUT_MAX_DELIVER = 5
INPUT_BACKOFF_SECONDS = [1, 5, 30]
INPUT_FETCH_BATCH = 10
INPUT_FETCH_TIMEOUT = 1.0


@dataclass(frozen=True)
class NatsDeliveryContext:
    stream: Optional[str]
    consumer: str
    subject: str
    sequence: Optional[int]
    delivery_count: int


class Machine:
    def __init__(
        self,
        projection: ProjectionStore,
        publisher: EventPublisher,
        executor: ModeExecutor,
        session_id: Optional[str] = None,
        runtime_store: Optional[RuntimeStore] = None,
    ) -> None:
        self.projection = projection
        self.publisher = publisher
        self.executor = executor
        self.session_id = session_id
        self._writer_lock = asyncio.Lock()
        self._nats_task: Optional[asyncio.Task] = None
        self._nats_metrics = NATS_METRICS
        self._listening = False
        self.runtime_store = runtime_store or RuntimeStore(user_id=projection.user_id)

    async def stop_listening(self) -> None:
        self._listening = False
        if self._nats_task:
            self._nats_task.cancel()
            try:
                await self._nats_task
            except asyncio.CancelledError:
                pass
            self._nats_task = None

    def _select_mode(self, prompt: str) -> ModeConfig:
        ahdb = self.projection.get_ahdb_state()
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

    async def handle_prompt(self, prompt: str, requested_run_id: Optional[str] = None) -> dict:
        work_item_id = str(uuid.uuid4())
        run_id = requested_run_id or str(uuid.uuid4())
        await self.publisher.publish(
            "run.input",
            {
                "prompt": prompt,
                "input_kind": "followup" if requested_run_id else "initial",
                "work_item_id": work_item_id,
                "run_id": run_id,
                "session_id": self.session_id,
            },
            source="user",
        )
        return {"work_item_id": work_item_id, "run_id": run_id}

    async def listen_for_inputs(self) -> bool:
        try:
            from .nats_client import get_nats_client

            nats_client = await get_nats_client()
            subject = build_subject(self.projection.user_id, "user", "run.input")
            durable = f"{INPUT_CONSUMER_PREFIX}-{self.projection.user_id}"
            config = ConsumerConfig(
                ack_policy="explicit",
                ack_wait=INPUT_ACK_WAIT_SECONDS,
                max_deliver=INPUT_MAX_DELIVER,
                backoff=INPUT_BACKOFF_SECONDS,
                deliver_policy="new",
            )
            subscription = await nats_client.pull_subscribe(subject, durable=durable, config=config)
            self._listening = True
            self._nats_task = asyncio.create_task(
                self._input_consumer_loop(subscription, durable)
            )
            return True
        except Exception as exc:
            logger.error("Failed to start input listener: %s", exc)
            return False

    async def _input_consumer_loop(self, subscription, consumer: str) -> None:
        while self._listening:
            try:
                msgs = await subscription.fetch(INPUT_FETCH_BATCH, timeout=INPUT_FETCH_TIMEOUT)
            except nats.errors.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("input consumer error: %s", exc)
                await asyncio.sleep(1)
                continue

            for msg in msgs:
                await self._handle_input_message(msg, consumer)

    async def _handle_input_message(self, msg, consumer: str) -> None:
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

        is_new, status = self.runtime_store.record_event_delivery(
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
            payload = event.payload or {}
            session_id = payload.get("session_id")
            if self.session_id and session_id and session_id != self.session_id:
                self.runtime_store.mark_event_done(consumer, event_id)
                await msg.ack()
                return

            if event.event_type != "run.input":
                self.runtime_store.mark_event_done(consumer, event_id)
                await msg.ack()
                return

            async with self._writer_lock:
                self.runtime_store.mark_event_processing(consumer, event_id)
                await self._handle_run_input(payload)
                self.runtime_store.mark_event_done(consumer, event_id)
                latency_ms = (time.monotonic() - started) * 1000
                await msg.ack()
                self._nats_metrics.record_ack(latency_ms)
                self._nats_metrics.record_handler_latency(latency_ms)
                self._log_delivery(context, event_id, "ack", "processed", latency_ms)
        except Exception as exc:
            self.runtime_store.mark_event_failed(consumer, event_id, str(exc))
            if delivery_count >= INPUT_MAX_DELIVER:
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

    async def _handle_run_input(self, payload: dict) -> None:
        prompt = payload.get("prompt") or ""
        work_item_id = payload.get("work_item_id") or str(uuid.uuid4())
        run_id = payload.get("run_id") or str(uuid.uuid4())
        mode_config = self._select_mode(prompt)

        directive = ModeDirective(
            mode_id=mode_config.mode_id,
            prompt=prompt,
            work_item_id=work_item_id,
            run_id=run_id,
            allow_write=mode_config.allow_write,
            session_id=self.session_id,
        )

        await self.publisher.publish(
            "run.started",
            {
                "mode": directive.mode_id,
                "work_item_id": directive.work_item_id,
                "run_id": directive.run_id,
                "session_id": directive.session_id,
            },
            source="system",
        )
        await self.publisher.publish(
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
        await self.publisher.publish(
            "mode.update",
            {
                "mode": directive.mode_id,
                "run_id": directive.run_id,
                "orchestrator_run_id": result.run_id,
                "status": result.status,
            },
            source="system",
        )
        await self.publisher.publish(
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
        await self.publisher.publish(
            "run.finished",
            {
                "mode": directive.mode_id,
                "work_item_id": directive.work_item_id,
                "run_id": directive.run_id,
                "status": result.status,
                "session_id": directive.session_id,
            },
            source="system",
        )

    async def _publish_dlq(self, event: ChoirEvent, context: NatsDeliveryContext, error: str) -> None:
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
        await self.publisher.publish_event(dlq_event)

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

    async def promote_ahdb_proposals(self, run_id: str) -> int:
        proposals = self.projection.list_ahdb_proposals(run_id)
        promoted = 0
        for proposal in proposals:
            if proposal.get("status") != "proposed":
                continue
            delta = proposal.get("delta")
            if not delta:
                continue
            await self.publisher.publish(
                "receipt.ahdb.delta",
                {
                    "delta": delta,
                    "run_id": run_id,
                    "authority": "asserted",
                    "evidence_run_id": run_id,
                },
                source="system",
            )
            promoted += 1
        return promoted
