import asyncio
import json
import logging
import signal
import sys
from pathlib import Path

import nats
from nats.js.api import ConsumerConfig

if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from supervisor.db import get_store
from supervisor.event_publisher import get_publisher
from supervisor.nats_client import ChoirEvent, get_nats_client
from supervisor.agent.auditor import UnilateralAuditor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("auditor-worker")

AUDITOR_CONSUMER_PREFIX = "auditor"
AUDITOR_ACK_WAIT_SECONDS = 30
AUDITOR_MAX_DELIVER = 5
AUDITOR_BACKOFF_SECONDS = [1, 5, 30]
AUDITOR_FETCH_BATCH = 10
AUDITOR_FETCH_TIMEOUT = 1.0


class AuditorWorker:
    def __init__(self):
        self.auditor = UnilateralAuditor()
        self.projection = get_store()
        self.publisher = get_publisher(self.projection.user_id)
        self.running = True
        self._listening = False
        self._nats_task: asyncio.Task | None = None

    async def start(self):
        logger.info("Starting Auditor Worker")
        try:
            nats_client = await get_nats_client()
            subject = f"choiros.{self.projection.user_id}.*.file.write"
            durable = f"{AUDITOR_CONSUMER_PREFIX}-{self.projection.user_id}"
            config = ConsumerConfig(
                ack_policy="explicit",
                ack_wait=AUDITOR_ACK_WAIT_SECONDS,
                max_deliver=AUDITOR_MAX_DELIVER,
                backoff=AUDITOR_BACKOFF_SECONDS,
                deliver_policy="new",
            )
            subscription = await nats_client.pull_subscribe(subject, durable=durable, config=config)
        except Exception as exc:
            logger.error("Auditor NATS connect failed: %s", exc)
            return

        self._listening = True
        self._nats_task = asyncio.create_task(self._consumer_loop(subscription))
        await self._nats_task

    async def _consumer_loop(self, subscription) -> None:
        while self._listening:
            try:
                msgs = await subscription.fetch(AUDITOR_FETCH_BATCH, timeout=AUDITOR_FETCH_TIMEOUT)
            except nats.errors.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Auditor consumer error: %s", exc)
                await asyncio.sleep(1)
                continue

            for msg in msgs:
                await self._handle_message(msg)

    async def _handle_message(self, msg) -> None:
        event = ChoirEvent.from_json(msg.data)
        if event.event_type != "file.write":
            await msg.ack()
            return
        try:
            payload = event.payload or {}
            path = payload.get("path", "")

            if any(x in path for x in [".git", "node_modules", ".DS_Store", "__pycache__"]):
                await msg.ack()
                return

            logger.info("Auditing change to: %s", path)
            result = await self.auditor.audit_file(path)

            await self.publisher.publish(
                "auditor.critique",
                {
                    "path": path,
                    "mode": result.mode,
                    "critique": result.critique,
                    "blind_spots": result.blind_spots,
                    "citations": result.citations,
                },
                source="system",
            )
            await msg.ack()
        except Exception as exc:
            logger.error("Error handling file write: %s", exc)
            await msg.nak()

    async def stop(self):
        self.running = False
        self._listening = False
        if self._nats_task:
            self._nats_task.cancel()


if __name__ == "__main__":
    worker = AuditorWorker()

    def signal_handler(*_args):
        asyncio.create_task(worker.stop())

    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        pass
