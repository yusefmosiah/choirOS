import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from supervisor.db import EventStore
from supervisor import main as supervisor_main
from supervisor.sandbox_runner import (
    SandboxCheckpoint,
    SandboxCommand,
    SandboxConfig,
    SandboxHandle,
    SandboxProcess,
    SandboxProxy,
    SandboxResult,
    SandboxRunner,
)


class FakeSandboxRunner(SandboxRunner):
    def __init__(self) -> None:
        self.handle = None
        self.commands = []
        self.created = 0
        self.destroyed = 0
        self.checkpoints = 0
        self.restores = 0

    def create(self, config: SandboxConfig) -> SandboxHandle:
        self.created += 1
        self.handle = SandboxHandle(sandbox_id="sbx-1", config=config)
        return self.handle

    def destroy(self, handle: SandboxHandle) -> None:
        self.destroyed += 1

    def checkpoint(self, handle: SandboxHandle, label: str | None = None) -> SandboxCheckpoint:
        self.checkpoints += 1
        return SandboxCheckpoint(checkpoint_id="ckpt-1", created_at="now", label=label)

    def restore(self, handle: SandboxHandle, checkpoint_id: str) -> None:
        self.restores += 1

    def run(self, command: SandboxCommand) -> SandboxResult:
        self.commands.append(command.command)
        return SandboxResult(return_code=0, stdout="ok", stderr="")

    def start_process(self, command: SandboxCommand) -> SandboxProcess:
        return SandboxProcess(process_id="proc-1", command=command.command, cwd=str(command.cwd) if command.cwd else None)

    def stop_process(self, handle: SandboxHandle, process_id: str) -> None:
        return None

    def open_proxy(self, handle: SandboxHandle, port: int) -> SandboxProxy:
        return SandboxProxy(url=f"http://sandbox.local:{port}", port=port)


class TestSupervisorSandboxEndpoints(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["NATS_ENABLED"] = "0"
        fd, self.db_path = tempfile.mkstemp(prefix="choiros_sbx_", suffix=".sqlite")
        os.close(fd)
        self.store = EventStore(db_path=Path(self.db_path), user_id="local")
        self.fake = FakeSandboxRunner()
        self.client = TestClient(supervisor_main.app)

    def tearDown(self) -> None:
        self.store.close()
        Path(self.db_path).unlink(missing_ok=True)

    def test_full_sandbox_lifecycle(self) -> None:
        with (
            mock.patch("supervisor.main.get_store", return_value=self.store),
            mock.patch("supervisor.main.get_sandbox_runner", return_value=self.fake),
        ):
            response = self.client.post("/sandbox/create", json={})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json().get("sandbox_id"), "sbx-1")

            response = self.client.post("/sandbox/exec", json={"command": ["echo", "ok"]})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json().get("return_code"), 0)

            response = self.client.post("/sandbox/exec", json={"command": ["sleep", "10"], "background": True})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json().get("process_id"), "proc-1")

            response = self.client.post("/sandbox/process/stop", json={"process_id": "proc-1"})
            self.assertEqual(response.status_code, 200)

            response = self.client.post("/sandbox/proxy", json={"port": 5173})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json().get("url"), "http://sandbox.local:5173")

            response = self.client.post("/sandbox/checkpoint", json={"label": "ok"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json().get("checkpoint_id"), "ckpt-1")

            response = self.client.post("/sandbox/restore", json={"checkpoint_id": "ckpt-1"})
            self.assertEqual(response.status_code, 200)

            response = self.client.post("/sandbox/destroy")
            self.assertEqual(response.status_code, 200)

        self.assertEqual(self.fake.created, 1)
        self.assertEqual(self.fake.destroyed, 1)
        self.assertEqual(self.fake.checkpoints, 1)
        self.assertEqual(self.fake.restores, 1)
