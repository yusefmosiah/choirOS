import asyncio
import os
import tempfile
import time
import unittest
import uuid
from pathlib import Path

try:
    import nats
    from nats.js.api import ConsumerConfig
except ImportError:
    nats = None
    ConsumerConfig = None

from supervisor.db import EventStore
from supervisor.event_contract import CHOIR_STREAM, build_subject
from supervisor.nats_client import NATSClient, ChoirEvent
from shared.tenancy import subject_prefix_for


def _nats_url() -> str:
    return os.environ.get("NATS_URL", "nats://localhost:4222")


class TestNatsIntegration(unittest.TestCase):
    def setUp(self) -> None:
        if nats is None or ConsumerConfig is None:
            self.skipTest("nats-py not installed; install supervisor requirements to run")
        if os.environ.get("RUN_NATS_TESTS") != "1":
            self.skipTest("Set RUN_NATS_TESTS=1 to run NATS integration tests")
        try:
            asyncio.run(self._check_nats())
        except Exception as exc:
            self.skipTest(f"NATS not reachable: {exc}")
        fd, self.db_path = tempfile.mkstemp(prefix="choiros_nats_", suffix=".sqlite")
        os.close(fd)
        self.store = EventStore(db_path=Path(self.db_path), user_id="local")

    def tearDown(self) -> None:
        self.store.close()
        Path(self.db_path).unlink(missing_ok=True)

    async def _check_nats(self) -> None:
        nc = await nats.connect(_nats_url())
        await nc.drain()

    def test_publish_dedup_by_msg_id(self) -> None:
        async def run():
            client = NATSClient(url=_nats_url())
            await client.connect()
            info = await client.js.stream_info(CHOIR_STREAM)
            start_seq = info.state.last_seq
            user_id = f"test-{uuid.uuid4()}"
            event = ChoirEvent(
                id=str(uuid.uuid4()),
                timestamp=int(time.time() * 1000),
                user_id=user_id,
                source="system",
                event_type="mode.start",
                payload={"work_item_id": "w1"},
            )
            await client.publish_event(event)
            await client.publish_event(event)
            events = await client.get_events(
                stream=CHOIR_STREAM,
                subject_filter=subject_prefix_for(user_id),
                start_seq=start_seq + 1,
                limit=10,
            )
            matches = [e for e, _ in events if e.id == event.id]
            await client.disconnect()
            self.assertEqual(len(matches), 1)

        asyncio.run(run())

    def test_redelivery_resume_after_no_ack(self) -> None:
        async def run():
            client = NATSClient(url=_nats_url())
            await client.connect()
            user_id = f"test-{uuid.uuid4()}"
            subject = build_subject(user_id, "system", "mode.start")
            durable = f"test-redeliver.{user_id}"
            config = ConsumerConfig(
                ack_policy="explicit",
                ack_wait=1_000_000_000,
                max_deliver=3,
                deliver_policy="new",
            )
            sub = await client.pull_subscribe(subject, durable=durable, config=config)

            event = ChoirEvent(
                id=str(uuid.uuid4()),
                timestamp=int(time.time() * 1000),
                user_id=user_id,
                source="system",
                event_type="mode.start",
                payload={"work_item_id": "w1"},
            )
            await client.publish_event(event)

            msgs = await sub.fetch(1, timeout=2)
            first = msgs[0]
            meta = first.metadata
            self.store.record_event_delivery(
                consumer=durable,
                event_id=event.id,
                nats_seq=meta.sequence.stream if meta else None,
                subject=first.subject,
                delivery_count=meta.num_delivered if meta else 1,
            )

            await asyncio.sleep(1.2)

            msgs = await sub.fetch(1, timeout=2)
            second = msgs[0]
            meta = second.metadata
            self.store.record_event_delivery(
                consumer=durable,
                event_id=event.id,
                nats_seq=meta.sequence.stream if meta else None,
                subject=second.subject,
                delivery_count=meta.num_delivered if meta else 1,
            )
            self.store.mark_event_processing(durable, event.id)
            self.store.mark_event_done(durable, event.id)
            await second.ack()

            row = self.store.conn.execute(
                "SELECT status, delivery_count FROM event_dedupe WHERE consumer = ? AND event_id = ?",
                (durable, event.id),
            ).fetchone()

            await client.js.delete_consumer(CHOIR_STREAM, durable)
            await client.disconnect()

            self.assertIsNotNone(row)
            self.assertEqual(row["status"], "done")
            self.assertGreaterEqual(row["delivery_count"], 2)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
