import os
import tempfile
import unittest
from pathlib import Path

from supervisor.db import EventStore


class TestAHDBProjection(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["NATS_ENABLED"] = "0"
        fd, self.db_path = tempfile.mkstemp(prefix="choiros_ahdb_", suffix=".sqlite")
        os.close(fd)
        self.store = EventStore(db_path=Path(self.db_path), user_id="local")

    def tearDown(self) -> None:
        self.store.close()
        Path(self.db_path).unlink(missing_ok=True)

    def test_rebuild_projection_from_events(self) -> None:
        delta1 = {
            "assert": [{"id": "a1", "text": "First assertion"}],
            "drive": [{"id": "d1", "text": "Prefer speed"}],
        }
        delta2 = {
            "assert": [{"id": "a2", "text": "Second assertion"}],
            "hypothesize": [{"id": "h1", "text": "Maybe flaky"}],
        }

        self.store.append("receipt.ahdb.delta", {"delta": delta1}, source="system")
        self.store.append("receipt.ahdb.delta", {"delta": delta2}, source="system")

        replayed = self.store.rebuild_projection_from_events()
        self.assertEqual(replayed, 2)

        state = self.store.get_ahdb_state()
        self.assertEqual(state.get("assert"), delta2["assert"])
        self.assertEqual(state.get("drive"), delta1["drive"])
        self.assertEqual(state.get("hypothesize"), delta2["hypothesize"])
        self.assertNotIn("believe", state)

        cursor = self.store.conn.execute("SELECT COUNT(*) FROM ahdb_deltas")
        self.assertEqual(cursor.fetchone()[0], 2)

    def test_log_ahdb_delta_updates_state(self) -> None:
        delta = {
            "believe": [{"id": "b1", "text": "Constraint"}],
        }
        seq = self.store.log_ahdb_delta(delta, {"run_id": "run-1"})
        self.assertGreater(seq, 0)

        state = self.store.get_ahdb_state()
        self.assertEqual(state.get("believe"), delta["believe"])

        cursor = self.store.conn.execute("SELECT COUNT(*) FROM ahdb_deltas")
        self.assertEqual(cursor.fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
