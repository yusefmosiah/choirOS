import tempfile
import unittest
from pathlib import Path
import asyncio

from supervisor.agent.tools import AgentTools
from supervisor.mode_config import ModeConfig, ModeBudgets
from supervisor.event_publisher import EventPublisher
from supervisor.tests.fakes import FakeNATSClient


class TestAgentTools(unittest.TestCase):
    def setUp(self) -> None:
        self.fake_nats = FakeNATSClient()
        self.publisher = EventPublisher(user_id="local", nats_client=self.fake_nats)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)
        self.tools = AgentTools(file_history=None, event_publisher=self.publisher)
        self.tools.app_dir = self.root
        self.tools.cwd = str(self.root)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_read_write_edit_file(self) -> None:
        asyncio.run(self.tools.write_file("notes.txt", "hello"))
        result = asyncio.run(self.tools.read_file("notes.txt"))
        self.assertEqual(result.get("content"), "hello")

        edit_result = asyncio.run(
            self.tools.edit_file(
                "notes.txt",
                [{"old_text": "hello", "new_text": "hi"}],
            )
        )
        self.assertTrue(edit_result.get("modified"))
        result = asyncio.run(self.tools.read_file("notes.txt"))
        self.assertEqual(result.get("content"), "hi")

    def test_edit_file_dry_run(self) -> None:
        (self.root / "demo.txt").write_text("alpha beta")
        result = asyncio.run(
            self.tools.edit_file(
                "demo.txt",
                [{"old_text": "beta", "new_text": "gamma"}],
                dry_run=True,
            )
        )
        self.assertTrue(result.get("dry_run"))
        self.assertEqual((self.root / "demo.txt").read_text(), "alpha beta")

    def test_write_emits_artifact_pointer(self) -> None:
        asyncio.run(self.tools.write_file("notes.txt", "hello"))
        pointer_events = [e.event for e in self.fake_nats.published if e.event.event_type == "artifact.pointer"]
        self.assertTrue(pointer_events)
        artifact_hash = pointer_events[0].payload.get("artifact_hash")
        self.assertTrue(artifact_hash)
        artifact = asyncio.run(self.tools.read_artifact(artifact_hash))
        self.assertIn("content", artifact)

    def test_mode_gating_blocks_writes(self) -> None:
        mode = ModeConfig(
            mode_id="CURIOUS",
            tool_allowlist=["read_file"],
            allow_write=False,
            allow_network=False,
            budgets=ModeBudgets(time_seconds=60, tool_calls=5, diff_bytes=0, files_touched=0),
        )
        tools = AgentTools(file_history=None, event_publisher=self.publisher, mode_config=mode)
        tools.app_dir = self.root
        tools.cwd = str(self.root)
        result = asyncio.run(tools.write_file("blocked.txt", "nope"))
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
