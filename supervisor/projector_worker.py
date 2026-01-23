"""JetStream projector worker for libsql projections."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add project root to path
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from supervisor.db import EventStore
from supervisor.nats_client import get_nats_client
from supervisor.event_contract import CHOIR_STREAM
from shared.tenancy import subject_prefix_for

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("projector-worker")


class ProjectorWorker:
    def __init__(self) -> None:
        self.store = EventStore()
        self.running = True
        self._cursor_key = "projector:last_nats_seq"

    def _get_start_seq(self) -> int:
        stored = self.store.get_sync_state(self._cursor_key)
        if stored and stored.isdigit():
            return int(stored)
        latest = self.store.get_latest_nats_seq()
        return int(latest or 0)

    def _set_cursor(self, seq: int) -> None:
        self.store.set_sync_state(self._cursor_key, str(seq))

    async def start(self) -> None:
        """Continuously project NATS events into the projection store."""
        start_seq = self._get_start_seq()
        logger.info("Starting projector. Last NATS seq: %s", start_seq)

        while self.running:
            try:
                nats = await get_nats_client()
            except Exception as exc:
                logger.error("Projector NATS connect failed: %s", exc)
                await asyncio.sleep(2)
                continue

            try:
                events = await nats.get_events(
                    stream=CHOIR_STREAM,
                    subject_filter=subject_prefix_for(self.store.user_id),
                    start_seq=start_seq + 1,
                    limit=500,
                )
                if not events:
                    await asyncio.sleep(0.5)
                    continue

                last_seq = start_seq
                for event, nats_seq in events:
                    if nats_seq is None:
                        continue
                    self.store.apply_event(event.event_type, event.payload, event.timestamp, nats_seq)
                    last_seq = max(last_seq, int(nats_seq))

                self.store.conn.commit()
                self._set_cursor(last_seq)
                start_seq = last_seq
            except Exception as exc:
                logger.error("Projector loop error: %s", exc)
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
