import os
import tempfile
import time
import unittest
from pathlib import Path

from supervisor.db import EventStore


class TestEventDedupe(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["NATS_ENABLED"] = "0"
        fd, self.db_path = tempfile.mkstemp(prefix="choiros_dedupe_", suffix=".sqlite")
        os.close(fd)
        self.store = EventStore(db_path=Path(self.db_path), user_id="local")

    def tearDown(self) -> None:
        self.store.close()
        Path(self.db_path).unlink(missing_ok=True)

    def test_dedupe_records_and_marks_done(self) -> None:
        event_id = "event-123"
        is_new, status = self.store.record_event_delivery(
            consumer="test-consumer",
            event_id=event_id,
            nats_seq=10,
            subject="choiros.local.system.mode.start",
            delivery_count=1,
        )
        self.assertTrue(is_new)
        self.assertEqual(status, "received")

        self.store.mark_event_processing("test-consumer", event_id)
        self.store.mark_event_done("test-consumer", event_id)

        is_new_again, status_again = self.store.record_event_delivery(
            consumer="test-consumer",
            event_id=event_id,
            nats_seq=10,
            subject="choiros.local.system.mode.start",
            delivery_count=2,
        )
        self.assertFalse(is_new_again)
        self.assertEqual(status_again, "done")

    def test_apply_event_dedupes_by_nats_seq(self) -> None:
        now_ms = int(time.time() * 1000)
        first = self.store.apply_event(
            "mode.start",
            {"work_item_id": "w1"},
            now_ms,
            nats_seq=5,
            event_id="event-1",
        )
        second = self.store.apply_event(
            "mode.start",
            {"work_item_id": "w1"},
            now_ms,
            nats_seq=5,
            event_id="event-2",
        )
        self.assertEqual(first, second)
        count = self.store.conn.execute("SELECT COUNT(*) FROM events WHERE nats_seq = 5").fetchone()[0]
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
