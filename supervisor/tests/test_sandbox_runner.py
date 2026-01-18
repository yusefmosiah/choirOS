import tempfile
import unittest
from pathlib import Path
import sys

from supervisor.sandbox_runner import (
    LocalSandboxRunner,
    SandboxCommand,
    SandboxConfig,
    SandboxNetworkPolicy,
    SandboxResources,
)


class TestSandboxRunner(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.workspace = tempfile.TemporaryDirectory()
        self.runner = LocalSandboxRunner(root=Path(self.tmp_dir.name))
        self.config = SandboxConfig(
            user_id="local",
            workspace_id="ws-1",
            workspace_root=self.workspace.name,
            env={"SANDBOX_TEST": "1"},
            resources=SandboxResources(cpu_cores=1.0, memory_mb=256, disk_mb=512),
            network_policy=SandboxNetworkPolicy(allow_internet=False),
        )

    def tearDown(self) -> None:
        self.workspace.cleanup()
        self.tmp_dir.cleanup()

    def test_create_checkpoint_restore_destroy(self) -> None:
        handle = self.runner.create(self.config)
        self.assertTrue((Path(self.tmp_dir.name) / handle.sandbox_id).exists())

        checkpoint = self.runner.checkpoint(handle, label="test")
        self.assertTrue(checkpoint.checkpoint_id)

        self.runner.restore(handle, checkpoint.checkpoint_id)
        with self.assertRaises(ValueError):
            self.runner.restore(handle, "missing")

        self.runner.destroy(handle)
        self.assertFalse((Path(self.tmp_dir.name) / handle.sandbox_id).exists())

    def test_run_uses_workspace_root(self) -> None:
        handle = self.runner.create(self.config)
        command = SandboxCommand(
            command=[sys.executable, "-c", "import os; print(os.getcwd())"],
            sandbox=handle,
        )
        result = self.runner.run(command)
        self.assertEqual(result.return_code, 0)
        self.assertEqual(
            Path(result.stdout.strip()).resolve(),
            Path(self.workspace.name).resolve(),
        )
