import os
import tempfile
import unittest
from pathlib import Path

from supervisor.db import EventStore


class TestRunsAndWorkItems(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["NATS_ENABLED"] = "0"
        fd, self.db_path = tempfile.mkstemp(prefix="choiros_run_", suffix=".sqlite")
        os.close(fd)
        self.store = EventStore(db_path=Path(self.db_path), user_id="local")

    def tearDown(self) -> None:
        self.store.close()
        Path(self.db_path).unlink(missing_ok=True)

    def test_work_item_create_update_list(self) -> None:
        item = self.store.create_work_item(
            description="Implement run persistence",
            acceptance_criteria="API returns created run",
            required_verifiers=["V-03-RUN-STATE"],
            risk_tier="low",
            dependencies=["SD-02"],
        )
        self.assertEqual(item["description"], "Implement run persistence")
        self.assertEqual(item["required_verifiers"], ["V-03-RUN-STATE"])

        updated = self.store.update_work_item(item["id"], {"status": "in_progress"})
        self.assertEqual(updated["status"], "in_progress")

        items = self.store.list_work_items()
        self.assertGreaterEqual(len(items), 1)

    def test_run_create_and_notes(self) -> None:
        item = self.store.create_work_item(description="Run item")
        run = self.store.create_run(item["id"], mood="CALM")
        self.assertEqual(run["work_item_id"], item["id"])
        self.assertEqual(run["mood"], "CALM")

        note_seq = self.store.add_run_note(run["id"], "note.status", {"status": "started"})
        self.assertGreater(note_seq, 0)

        verification_seq = self.store.add_run_verification(run["id"], {"result": "pass"})
        self.assertGreater(verification_seq, 0)

        commit_seq = self.store.add_commit_request(run["id"], {"verifiers": ["V-03-RUN-STATE"]})
        self.assertGreater(commit_seq, 0)

        cursor = self.store.conn.execute("SELECT COUNT(*) FROM run_notes")
        self.assertEqual(cursor.fetchone()[0], 1)
        cursor = self.store.conn.execute("SELECT COUNT(*) FROM run_verifications")
        self.assertEqual(cursor.fetchone()[0], 1)
        cursor = self.store.conn.execute("SELECT COUNT(*) FROM run_commit_requests")
        self.assertEqual(cursor.fetchone()[0], 1)

    def test_projection_rebuild_populates_run_notes(self) -> None:
        item = self.store.create_work_item(description="Projection test")
        run = self.store.create_run(item["id"], mood="CURIOUS")
        self.store.add_run_note(run["id"], "note.observation", {"body": "hello"})

        rebuilt = self.store.rebuild_projection_from_events()
        self.assertEqual(rebuilt, 1)

        cursor = self.store.conn.execute("SELECT COUNT(*) FROM run_notes")
        self.assertEqual(cursor.fetchone()[0], 1)

    def test_event_paths_since(self) -> None:
        start_seq = self.store.get_latest_seq()
        self.store.log_file_write("notes/demo.txt", b"demo")
        paths = self.store.get_event_paths_since(start_seq)
        self.assertIn("notes/demo.txt", paths)


if __name__ == "__main__":
    unittest.main()
