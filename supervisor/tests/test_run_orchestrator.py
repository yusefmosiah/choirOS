import os
import tempfile
import unittest
from pathlib import Path
import sys

from supervisor.db import EventStore
from supervisor.run_orchestrator import RunOrchestrator
from supervisor.verifier_runner import ArtifactStore, VerifierRunner, VerifierSpec


class TestRunOrchestrator(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["NATS_ENABLED"] = "0"
        fd, self.db_path = tempfile.mkstemp(prefix="choiros_orch_", suffix=".sqlite")
        os.close(fd)
        self.store = EventStore(db_path=Path(self.db_path), user_id="local")
        self.artifacts = tempfile.TemporaryDirectory()
        self.runner = VerifierRunner(store=ArtifactStore(root=Path(self.artifacts.name)))
        self.orchestrator = RunOrchestrator(store=self.store, verifier_runner=self.runner)

    def tearDown(self) -> None:
        self.store.close()
        Path(self.db_path).unlink(missing_ok=True)
        self.artifacts.cleanup()

    def test_orchestrator_success_flow(self) -> None:
        work_item = self.store.create_work_item(description="Orchestrator test")

        def execute_run(_: dict) -> bool:
            return True

        specs = [
            VerifierSpec(
                verifier_id="V-TEST-PASS",
                command=[sys.executable, "-c", "print('ok')"],
            )
        ]

        result = self.orchestrator.run(
            work_item_id=work_item["id"],
            execute_run=execute_run,
            verifier_specs=specs,
        )

        run = result["run"]
        self.assertEqual(run["status"], "verified")
        self.assertEqual(run["mood"], "SKEPTICAL")

        cursor = self.store.conn.execute("SELECT COUNT(*) FROM run_verifications")
        self.assertEqual(cursor.fetchone()[0], 1)
        cursor = self.store.conn.execute("SELECT COUNT(*) FROM run_commit_requests")
        self.assertEqual(cursor.fetchone()[0], 1)

    def test_orchestrator_failure_flow(self) -> None:
        work_item = self.store.create_work_item(description="Orchestrator fail")

        def execute_run(_: dict) -> bool:
            return False

        result = self.orchestrator.run(
            work_item_id=work_item["id"],
            execute_run=execute_run,
            verifier_specs=[],
        )

        run = result["run"]
        self.assertEqual(run["status"], "failed")
        cursor = self.store.conn.execute("SELECT COUNT(*) FROM run_commit_requests")
        self.assertEqual(cursor.fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
