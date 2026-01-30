"""JetStream projector worker for libsql projections."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path

import nats
from nats.js.api import ConsumerConfig

if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from supervisor.db import ProjectionStore
from supervisor.nats_client import ChoirEvent, get_nats_client
from shared.tenancy import subject_prefix_for

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("projector-worker")

PROJECTOR_ACK_WAIT_SECONDS = 30
PROJECTOR_MAX_DELIVER = 5
PROJECTOR_BACKOFF_SECONDS = [1, 5, 30]
PROJECTOR_FETCH_BATCH = 200
PROJECTOR_FETCH_TIMEOUT = 1.0


class ProjectorWorker:
    def __init__(self, store: ProjectionStore | None = None) -> None:
        self.store = store or ProjectionStore()
        self.running = True
        self.consumer = f"projector-{self.store.user_id}"

    def _get_last_seq(self) -> int:
        stored = self.store.get_projection_state("last_nats_seq")
        if stored and stored.isdigit():
            return int(stored)
        latest = self.store.get_latest_nats_seq()
        return int(latest or 0)

    async def start(self) -> None:
        last_seq = self._get_last_seq()
        logger.info("Starting projector. Last NATS seq: %s", last_seq)

        while self.running:
            try:
                nats_client = await get_nats_client()
                subject = subject_prefix_for(self.store.user_id)
                config = ConsumerConfig(
                    ack_policy="explicit",
                    ack_wait=PROJECTOR_ACK_WAIT_SECONDS,
                    max_deliver=PROJECTOR_MAX_DELIVER,
                    backoff=PROJECTOR_BACKOFF_SECONDS,
                    deliver_policy="all",
                )
                subscription = await nats_client.pull_subscribe(
                    subject,
                    durable=self.consumer,
                    config=config,
                )
            except Exception as exc:
                logger.error("Projector NATS connect failed: %s", exc)
                await asyncio.sleep(2)
                continue

            while self.running:
                try:
                    msgs = await subscription.fetch(PROJECTOR_FETCH_BATCH, timeout=PROJECTOR_FETCH_TIMEOUT)
                except nats.errors.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.error("Projector fetch error: %s", exc)
                    await asyncio.sleep(2)
                    continue

                if not msgs:
                    continue

                try:
                    batch_last = None
                    for msg in msgs:
                        event = ChoirEvent.from_json(msg.data)
                        metadata = msg.metadata
                        nats_seq = metadata.sequence.stream if metadata else None
                        if nats_seq is None:
                            await msg.ack()
                            continue
                        self.store.apply_event(event.event_type, event.payload, event.timestamp, nats_seq, event.id)
                        batch_last = nats_seq if batch_last is None else max(batch_last, nats_seq)

                    if batch_last is not None:
                        self.store.set_projection_state("last_nats_seq", str(batch_last), commit=False)
                    self.store.conn.commit()

                    for msg in msgs:
                        await msg.ack()

                    if batch_last is not None:
                        last_seq = batch_last
                except Exception as exc:
                    logger.error("Projector apply error: %s", exc)
                    await asyncio.sleep(2)

    async def stop(self) -> None:
        self.running = False


if __name__ == "__main__":
    worker = ProjectorWorker()

    def signal_handler(*_args):
        asyncio.create_task(worker.stop())

    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        pass
