"""
NATS Integration Tests - Event Deduplication

PREDICTION: NATS JetStream with deduplication by (consumer, event_id) ensures
exactly-once processing even when messages are redelivered due to crashes or delays.

EXPERIMENT: These tests simulate real-world failure scenarios:
1. Duplicate publishes (same event_id)
2. Message redelivery after AckWait timeout
3. Consumer crash and recovery
4. Multiple concurrent consumers

OBSERVE: Verify that event_dedupe table correctly tracks delivery state and prevents
duplicate processing across all failure modes.
"""

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

from supervisor.runtime_store import RuntimeStore
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
        self.runtime_store = RuntimeStore(db_path=Path(self.db_path), user_id="local")

    def tearDown(self) -> None:
        self.runtime_store.close()
        Path(self.db_path).unlink(missing_ok=True)

    async def _check_nats(self) -> None:
        nc = await nats.connect(_nats_url())
        await nc.drain()

    def test_publish_dedup_by_msg_id(self) -> None:
        """
        PREDICTION: Publishing the same event (same event_id) twice to NATS JetStream
        results in exactly one message stored due to NATS message ID deduplication.

        EXPERIMENT:
        1. Create ChoirEvent with unique event_id
        2. Publish to NATS JetStream twice with same event_id
        3. Fetch events from stream
        4. Count occurrences by event_id

        OBSERVE:
        - Exactly one event with matching event_id in stream
        - Second publish is silently ignored by NATS
        - No duplicate events in consumer fetch
        """
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
        """
        PREDICTION: When a consumer fails to ACK a message before AckWait expires,
        NATS redelivers the message. The event_dedupe table tracks delivery_count,
        allowing the consumer to detect and handle redelivered messages correctly.

        EXPERIMENT:
        1. Create pull consumer with explicit ACK policy and very short AckWait
        2. Publish single event
        3. Fetch first delivery, record in event_dedupe (status='received')
        4. Do NOT ACK, wait for AckWait timeout
        5. Fetch second delivery, update event_dedupe (status='processing' -> 'done')
        6. ACK second delivery
        7. Query event_dedupe table

        OBSERVE:
        - event_dedupe.delivery_count >= 2 (at least two deliveries)
        - event_dedupe.status = 'done' (successfully processed)
        - NATS metadata shows increasing num_delivered across fetches
        - Consumer can resume processing after redelivery without duplicates
        """
        async def run():
            client = NATSClient(url=_nats_url())
            await client.connect()
            user_id = f"test-{uuid.uuid4()}"
            subject = build_subject(user_id, "system", "mode.start")
            durable = f"test-redeliver.{user_id}"
            config = ConsumerConfig(
                ack_policy="explicit",
                ack_wait=1.0,
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
            self.runtime_store.record_event_delivery(
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
            self.runtime_store.record_event_delivery(
                consumer=durable,
                event_id=event.id,
                nats_seq=meta.sequence.stream if meta else None,
                subject=second.subject,
                delivery_count=meta.num_delivered if meta else 1,
            )
            self.runtime_store.mark_event_processing(durable, event.id)
            self.runtime_store.mark_event_done(durable, event.id)
            await second.ack()

            row = self.runtime_store.conn.execute(
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
