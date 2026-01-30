import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from supervisor.db import ProjectionStore


class TestAHDBProjection(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.db_path = tempfile.mkstemp(prefix="choiros_ahdb_", suffix=".sqlite")
        os.close(fd)
        self.store = ProjectionStore(
            db_path=Path(self.db_path),
            user_id="local",
        )

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

        now = int(datetime.now().timestamp() * 1000)
        self.store.apply_event("receipt.ahdb.delta", {"delta": delta1}, now)
        self.store.apply_event("receipt.ahdb.delta", {"delta": delta2}, now)
        self.store.conn.commit()

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
        seq = self.store.apply_event(
            "receipt.ahdb.delta",
            {"delta": delta, "run_id": "run-1"},
            int(datetime.now().timestamp() * 1000),
        )
        self.store.conn.commit()
        self.assertGreater(seq, 0)

        state = self.store.get_ahdb_state()
        self.assertEqual(state.get("believe"), delta["believe"])

        cursor = self.store.conn.execute("SELECT COUNT(*) FROM ahdb_deltas")
        self.assertEqual(cursor.fetchone()[0], 1)

    def test_proposed_delta_does_not_update_state(self) -> None:
        delta = {
            "assert": [{"id": "a1", "text": "Proposed assertion"}],
        }
        seq = self.store.apply_event(
            "receipt.ahdb.delta",
            {"delta": delta, "authority": "proposed", "run_id": "run-2"},
            int(datetime.now().timestamp() * 1000),
        )
        self.store.conn.commit()
        self.assertGreater(seq, 0)

        state = self.store.get_ahdb_state()
        self.assertNotIn("assert", state)

        cursor = self.store.conn.execute("SELECT COUNT(*) FROM ahdb_proposals")
        self.assertEqual(cursor.fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
