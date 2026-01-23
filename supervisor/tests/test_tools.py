import os
import tempfile
import unittest
from pathlib import Path
import asyncio
import json

from supervisor.agent.tools import AgentTools
from supervisor.mode_config import ModeConfig, ModeBudgets
from supervisor.db import EventStore


class TestAgentTools(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["NATS_ENABLED"] = "0"
        fd, self.db_path = tempfile.mkstemp(prefix="choiros_tools_", suffix=".sqlite")
        os.close(fd)
        self.store = EventStore(db_path=Path(self.db_path), user_id="local")
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)
        self.tools = AgentTools(file_history=None, event_store=self.store)
        self.tools.app_dir = self.root
        self.tools.cwd = str(self.root)

    def tearDown(self) -> None:
        self.store.close()
        Path(self.db_path).unlink(missing_ok=True)
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
        events = self.store.get_events(event_type="artifact.pointer", limit=10)
        self.assertTrue(events)
        payload = events[0].get("payload")
        if isinstance(payload, str):
            payload = json.loads(payload)
        artifact_hash = payload.get("artifact_hash")
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
        tools = AgentTools(file_history=None, event_store=self.store, mode_config=mode)
        tools.app_dir = self.root
        tools.cwd = str(self.root)
        result = asyncio.run(tools.write_file("blocked.txt", "nope"))
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
