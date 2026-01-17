import os
import tempfile
import unittest
from pathlib import Path
import asyncio

from supervisor.agent.tools import AgentTools
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


if __name__ == "__main__":
    unittest.main()
