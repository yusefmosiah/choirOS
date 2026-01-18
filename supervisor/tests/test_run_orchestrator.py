import os
import tempfile
import unittest
from pathlib import Path
import sys
from unittest import mock

from supervisor.db import EventStore
from supervisor.run_orchestrator import RunOrchestrator
from supervisor.verifier_runner import ArtifactStore, VerifierRunner, VerifierSpec
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
        os.environ["NATS_ENABLED"] = "0"
        fd, self.db_path = tempfile.mkstemp(prefix="choiros_orch_", suffix=".sqlite")
        os.close(fd)
        self.store = EventStore(db_path=Path(self.db_path), user_id="local")
        self.artifacts = tempfile.TemporaryDirectory()
        self.fake_sandbox = FakeSandboxRunner()
        self.runner = VerifierRunner(
            store=ArtifactStore(root=Path(self.artifacts.name)),
            sandbox_runner=self.fake_sandbox,
        )
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
        self.assertEqual(len(self.fake_sandbox.created), 1)
        self.assertEqual(len(self.fake_sandbox.checkpoints), 1)
        self.assertEqual(len(self.fake_sandbox.destroyed), 1)

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
        self.assertEqual(len(self.fake_sandbox.created), 1)
        self.assertEqual(len(self.fake_sandbox.destroyed), 1)
        cursor = self.store.conn.execute("SELECT COUNT(*) FROM run_commit_requests")
        self.assertEqual(cursor.fetchone()[0], 0)

    def test_orchestrator_verifier_fail_triggers_sandbox_restore(self) -> None:
        work_item = self.store.create_work_item(description="Orchestrator verify fail")

        def execute_run(_: dict) -> bool:
            return True

        self.fake_sandbox.next_run_result = SandboxResult(return_code=1, stdout="bad", stderr="fail")
        self.store.set_sync_state("sandbox_checkpoint:local", "ckpt-1")

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

        run = result["run"]
        self.assertEqual(run["status"], "failed")
        self.assertEqual(len(self.fake_sandbox.restores), 2)


if __name__ == "__main__":
    unittest.main()
