import os
import tempfile
import unittest
from pathlib import Path

from supervisor.db import EventStore
from supervisor.replay import ReplayToolCache


class TestReplayMode(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["NATS_ENABLED"] = "0"
        fd, self.db_path = tempfile.mkstemp(prefix="choiros_replay_", suffix=".sqlite")
        os.close(fd)
        self.store = EventStore(db_path=Path(self.db_path), user_id="local")

    def tearDown(self) -> None:
        self.store.close()
        Path(self.db_path).unlink(missing_ok=True)

    def test_replay_tool_cache_returns_results_in_order(self) -> None:
        conversation_id = self.store.start_conversation()
        self.store.log_tool_call(
            conversation_id,
            "read_file",
            {"path": "a.txt"},
            {"content": "one"},
        )
        self.store.log_tool_call(
            conversation_id,
            "read_file",
            {"path": "a.txt"},
            {"content": "two"},
        )

        cache = ReplayToolCache.from_store(self.store, conversation_id)
        first = cache.get("read_file", {"path": "a.txt"})
        second = cache.get("read_file", {"path": "a.txt"})
        third = cache.get("read_file", {"path": "a.txt"})

        self.assertEqual(first, {"content": "one"})
        self.assertEqual(second, {"content": "two"})
        self.assertIsNone(third)

    def test_replay_message_order(self) -> None:
        conversation_id = self.store.start_conversation()
        self.store.add_message(conversation_id, "user", "hello")
        self.store.add_message(conversation_id, "assistant", "hi")
        messages = self.store.get_conversation_messages(conversation_id, limit=10)
        roles = [msg["role"] for msg in messages]
        contents = [msg["content"] for msg in messages]
        self.assertEqual(roles, ["user", "assistant"])
        self.assertEqual(contents, ["hello", "hi"])


if __name__ == "__main__":
    unittest.main()
