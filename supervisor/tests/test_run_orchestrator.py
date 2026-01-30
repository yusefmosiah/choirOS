"""
Run Orchestrator Tests

PREDICTION: Orchestrator runs reuse the work_item run_id and emit verifier outcomes
without creating divergent runs.

EXPERIMENT: Execute success/failure paths for a work item with a pre-created run.

OBSERVE: The resulting run id matches the work item run_id and statuses update.
"""

import os
import tempfile
import unittest
from pathlib import Path
import sys
from unittest import mock

from supervisor.db import ProjectionStore
from supervisor.event_publisher import EventPublisher
from supervisor.run_orchestrator import RunOrchestrator
from supervisor.runtime_store import RuntimeStore
from supervisor.verifier_runner import ArtifactStore, VerifierRunner, VerifierSpec
from supervisor.tests.fakes import FakeNATSClient
from supervisor.sandbox_runner import (
    SandboxCheckpoint,
    SandboxCommand,
    SandboxConfig,
    SandboxHandle,
    SandboxResult,
    SandboxRunner,
)


class FakeSandboxRunner(SandboxRunner):
    def __init__(self) -> None:
        self.created: list[SandboxConfig] = []
        self.destroyed: list[SandboxHandle] = []
        self.checkpoints: list[SandboxCheckpoint] = []
        self.restores: list[tuple[SandboxHandle, str]] = []
        self.next_run_result = SandboxResult(return_code=0, stdout="ok", stderr="")

    def create(self, config: SandboxConfig) -> SandboxHandle:
        self.created.append(config)
        return SandboxHandle(sandbox_id="fake-sandbox", config=config)

    def destroy(self, handle: SandboxHandle) -> None:
        self.destroyed.append(handle)

    def checkpoint(self, handle: SandboxHandle, label: str | None = None) -> SandboxCheckpoint:
        checkpoint = SandboxCheckpoint(checkpoint_id="ckpt-1", created_at="now", label=label)
        self.checkpoints.append(checkpoint)
        return checkpoint

    def restore(self, handle: SandboxHandle, checkpoint_id: str) -> None:
        self.restores.append((handle, checkpoint_id))

    def run(self, command: SandboxCommand) -> SandboxResult:
        return self.next_run_result


class TestRunOrchestrator(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.db_path = tempfile.mkstemp(prefix="choiros_orch_", suffix=".sqlite")
        os.close(fd)
        self.store = ProjectionStore(
            db_path=Path(self.db_path),
            user_id="local",
        )
        self.fake_nats = FakeNATSClient()
        self.publisher = EventPublisher(user_id="local", nats_client=self.fake_nats)
        self.runtime_store = RuntimeStore(db_path=Path(self.db_path), user_id="local")
        self.artifacts = tempfile.TemporaryDirectory()
        self.fake_sandbox = FakeSandboxRunner()
        self.runner = VerifierRunner(
            store=ArtifactStore(root=Path(self.artifacts.name)),
            sandbox_runner=self.fake_sandbox,
        )
        self.orchestrator = RunOrchestrator(
            projection=self.store,
            publisher=self.publisher,
            verifier_runner=self.runner,
            runtime_store=self.runtime_store,
        )

    def tearDown(self) -> None:
        self.store.close()
        Path(self.db_path).unlink(missing_ok=True)
        self.artifacts.cleanup()

    def _apply_published_events(self) -> None:
        for published in self.fake_nats.published:
            event = published.event
            self.store.apply_event(
                event.event_type,
                event.payload,
                event.timestamp,
                nats_seq=published.seq,
                event_id=event.id,
            )
        self.store.conn.commit()

    def test_orchestrator_success_flow(self) -> None:
        work_item = self.store.create_work_item(description="Orchestrator test")
        expected_run_id = work_item["run_id"]

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

        self._apply_published_events()
        run = self.store.get_run(expected_run_id)
        self.assertEqual(run["id"], expected_run_id)
        self.assertEqual(run["status"], "verified")
        self.assertEqual(run["mode"], "SKEPTICAL")
        self.assertEqual(len(self.fake_sandbox.created), 1)
        self.assertEqual(len(self.fake_sandbox.checkpoints), 1)
        self.assertEqual(len(self.fake_sandbox.destroyed), 1)

        cursor = self.store.conn.execute("SELECT COUNT(*) FROM run_verifications")
        self.assertEqual(cursor.fetchone()[0], 1)
        cursor = self.store.conn.execute("SELECT COUNT(*) FROM run_commit_requests")
        self.assertEqual(cursor.fetchone()[0], 1)

    def test_orchestrator_failure_flow(self) -> None:
        work_item = self.store.create_work_item(description="Orchestrator fail")
        expected_run_id = work_item["run_id"]

        def execute_run(_: dict) -> bool:
            return False

        result = self.orchestrator.run(
            work_item_id=work_item["id"],
            execute_run=execute_run,
            verifier_specs=[],
        )

        self._apply_published_events()
        run = self.store.get_run(expected_run_id)
        self.assertEqual(run["id"], expected_run_id)
        self.assertEqual(run["status"], "failed")
        self.assertEqual(len(self.fake_sandbox.created), 1)
        self.assertEqual(len(self.fake_sandbox.destroyed), 1)
        cursor = self.store.conn.execute("SELECT COUNT(*) FROM run_commit_requests")
        self.assertEqual(cursor.fetchone()[0], 0)

    def test_orchestrator_verifier_fail_triggers_sandbox_restore(self) -> None:
        work_item = self.store.create_work_item(description="Orchestrator verify fail")

        def execute_run(_: dict) -> bool:
            return True

        self.fake_sandbox.next_run_result = SandboxResult(return_code=1, stdout="bad", stderr="fail")
        self.runtime_store.set_state("sandbox_checkpoint:local", "ckpt-1")

        specs = [
            VerifierSpec(
                verifier_id="V-TEST-FAIL",
                command=[sys.executable, "-c", "print('bad')"],
            )
        ]

        with mock.patch("supervisor.run_orchestrator.git_revert", return_value={"success": True}):
            result = self.orchestrator.run(
                work_item_id=work_item["id"],
                execute_run=execute_run,
                verifier_specs=specs,
            )

        self._apply_published_events()
        run = self.store.get_run(result["run"]["id"])
        self.assertEqual(run["status"], "failed")
        self.assertEqual(len(self.fake_sandbox.restores), 2)


if __name__ == "__main__":
    unittest.main()
