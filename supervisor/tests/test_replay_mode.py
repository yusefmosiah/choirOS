import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from supervisor.db import ProjectionStore
from supervisor.replay import ReplayToolCache


class TestReplayMode(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.db_path = tempfile.mkstemp(prefix="choiros_replay_", suffix=".sqlite")
        os.close(fd)
        self.store = ProjectionStore(
            db_path=Path(self.db_path),
            user_id="local",
        )

    def tearDown(self) -> None:
        self.store.close()
        Path(self.db_path).unlink(missing_ok=True)

    def test_replay_tool_cache_returns_results_in_order(self) -> None:
        conversation_id = 3003
        now = int(datetime.now().timestamp() * 1000)
        self.store.apply_event(
            "tool.call",
            {
                "conversation_id": conversation_id,
                "tool_name": "read_file",
                "tool_input": {"path": "a.txt"},
                "tool_result": {"content": "one"},
            },
            now,
        )
        self.store.apply_event(
            "tool.call",
            {
                "conversation_id": conversation_id,
                "tool_name": "read_file",
                "tool_input": {"path": "a.txt"},
                "tool_result": {"content": "two"},
            },
            now,
        )
        self.store.conn.commit()

        cache = ReplayToolCache.from_store(self.store, conversation_id)
        first = cache.get("read_file", {"path": "a.txt"})
        second = cache.get("read_file", {"path": "a.txt"})
        third = cache.get("read_file", {"path": "a.txt"})

        self.assertEqual(first, {"content": "one"})
        self.assertEqual(second, {"content": "two"})
        self.assertIsNone(third)

    def test_replay_message_order(self) -> None:
        conversation_id = 4004
        now = int(datetime.now().timestamp() * 1000)
        self.store.apply_event(
            "message",
            {"conversation_id": conversation_id, "role": "user", "content": "hello"},
            now,
        )
        self.store.apply_event(
            "message",
            {"conversation_id": conversation_id, "role": "assistant", "content": "hi"},
            now,
        )
        self.store.conn.commit()
        messages = self.store.get_conversation_messages(conversation_id, limit=10)
        roles = [msg["role"] for msg in messages]
        contents = [msg["content"] for msg in messages]
        self.assertEqual(roles, ["user", "assistant"])
        self.assertEqual(contents, ["hello", "hi"])


if __name__ == "__main__":
    unittest.main()
