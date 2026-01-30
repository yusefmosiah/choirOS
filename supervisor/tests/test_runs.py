"""
Run Persistence Tests

PREDICTION: Run inputs emitted as events project into run_inputs for replay,
and run metadata persists consistently across work items and projections.

EXPERIMENT: Create work items, runs, and emit run.input events.

OBSERVE: run_inputs rows materialize from events and run metadata remains consistent.
"""

import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from supervisor.db import ProjectionStore


class TestRunsAndWorkItems(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.db_path = tempfile.mkstemp(prefix="choiros_run_", suffix=".sqlite")
        os.close(fd)
        self.store = ProjectionStore(
            db_path=Path(self.db_path),
            user_id="local",
        )

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
        run = self.store.create_run(item["id"], mode="CALM")
        self.assertEqual(run["work_item_id"], item["id"])
        self.assertEqual(run["mode"], "CALM")

        self.store.apply_event(
            "note.status",
            {"run_id": run["id"], "body": {"status": "started"}},
            int(datetime.now().timestamp() * 1000),
        )
        self.store.apply_event(
            "receipt.verifier.attestations",
            {"run_id": run["id"], "attestation": {"result": "pass"}},
            int(datetime.now().timestamp() * 1000),
        )
        self.store.apply_event(
            "note.request.verify",
            {"run_id": run["id"], "body": {"verifiers": ["V-03-RUN-STATE"]}},
            int(datetime.now().timestamp() * 1000),
        )
        self.store.conn.commit()

        cursor = self.store.conn.execute("SELECT COUNT(*) FROM run_notes")
        self.assertEqual(cursor.fetchone()[0], 2)
        cursor = self.store.conn.execute("SELECT COUNT(*) FROM run_verifications")
        self.assertEqual(cursor.fetchone()[0], 1)
        cursor = self.store.conn.execute("SELECT COUNT(*) FROM run_commit_requests")
        self.assertEqual(cursor.fetchone()[0], 1)

    def test_projection_rebuild_populates_run_notes(self) -> None:
        item = self.store.create_work_item(description="Projection test")
        run = self.store.create_run(item["id"], mode="CURIOUS")
        self.store.apply_event(
            "note.observation",
            {"run_id": run["id"], "body": {"body": "hello"}},
            int(datetime.now().timestamp() * 1000),
        )
        self.store.conn.commit()

        rebuilt = self.store.rebuild_projection_from_events()
        self.assertEqual(rebuilt, 1)

        cursor = self.store.conn.execute("SELECT COUNT(*) FROM run_notes")
        self.assertEqual(cursor.fetchone()[0], 1)

    def test_event_paths_since(self) -> None:
        start_seq = self.store.get_latest_seq()
        self.store.apply_event(
            "file.write",
            {"path": "notes/demo.txt", "content_hash": "demo"},
            int(datetime.now().timestamp() * 1000),
        )
        paths = self.store.get_event_paths_since(start_seq)
        self.assertIn("notes/demo.txt", paths)

    def test_run_timeline(self) -> None:
        item = self.store.create_work_item(description="Timeline test")
        run = self.store.create_run(item["id"], mode="CALM")

        self.store.apply_event(
            "note.status",
            {"run_id": run["id"], "body": {"status": "started"}},
            int(datetime.now().timestamp() * 1000),
        )
        self.store.apply_event(
            "note.observation",
            {"run_id": run["id"], "body": {"body": "testing"}},
            int(datetime.now().timestamp() * 1000),
        )
        self.store.apply_event(
            "receipt.verifier.attestations",
            {"run_id": run["id"], "attestation": {"result": "pass", "verifier": "V-01"}},
            int(datetime.now().timestamp() * 1000),
        )
        self.store.conn.commit()

        timeline = self.store.get_run_timeline(run["id"])
        self.assertEqual(timeline["run"]["id"], run["id"])
        self.assertEqual(len(timeline["notes"]), 2)
        self.assertEqual(len(timeline["verifications"]), 1)
        self.assertEqual(timeline["notes"][0]["note_type"], "note.status")
        self.assertEqual(timeline["notes"][1]["note_type"], "note.observation")
        self.assertEqual(timeline["verifications"][0]["attestation"]["verifier"], "V-01")

    def test_run_timeline_not_found(self) -> None:
        timeline = self.store.get_run_timeline("nonexistent-run-id")
        self.assertIsNone(timeline["run"])
        self.assertEqual(timeline["notes"], [])
        self.assertEqual(timeline["verifications"], [])

    def test_run_input_event_projects_run_inputs(self) -> None:
        """
        PREDICTION: A run.input event projects into run_inputs for replayable inputs.

        EXPERIMENT:
        1. Emit run.input with prompt, kind, and run_id.
        2. Query run_inputs for that run_id.

        OBSERVE:
        - One run input row exists.
        - Prompt and kind match the event payload.
        """
        run_id = "run-123"
        self.store.apply_event(
            "run.input",
            {
                "prompt": "hello",
                "input_kind": "initial",
                "run_id": run_id,
                "work_item_id": "work-123",
            },
            int(datetime.now().timestamp() * 1000),
        )
        self.store.conn.commit()
        inputs = self.store.list_run_inputs(run_id)
        self.assertEqual(len(inputs), 1)
        self.assertEqual(inputs[0]["prompt"], "hello")
        self.assertEqual(inputs[0]["kind"], "initial")

    def test_claim_next_work_item_respects_runner_id(self) -> None:
        """
        PREDICTION: Work items assigned to a runner_id are only claimed by that runner.

        EXPERIMENT:
        1. Create two queued work items with distinct runner_id values.
        2. Claim with runner-a, then attempt claim with runner-c.

        OBSERVE:
        - runner-a claims its own work item.
        - runner-c receives no work item when none are unassigned.
        """
        item_a = self.store.create_work_item(
            description="Runner A item",
            status="queued",
            runner_id="runner-a",
        )
        self.store.create_work_item(
            description="Runner B item",
            status="queued",
            runner_id="runner-b",
        )

        claimed_a = self.store.claim_next_work_item("runner-a")
        self.assertIsNotNone(claimed_a)
        self.assertEqual(claimed_a["id"], item_a["id"])

        claimed_c = self.store.claim_next_work_item("runner-c")
        self.assertIsNone(claimed_c)


if __name__ == "__main__":
    unittest.main()
