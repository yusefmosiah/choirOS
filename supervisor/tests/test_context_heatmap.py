import os
import tempfile
import unittest
from pathlib import Path

from supervisor.db import EventStore


class TestContextHeatmap(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["NATS_ENABLED"] = "0"
        fd, self.db_path = tempfile.mkstemp(prefix="choiros_heatmap_", suffix=".sqlite")
        os.close(fd)
        self.store = EventStore(db_path=Path(self.db_path), user_id="local")

    def tearDown(self) -> None:
        self.store.close()
        Path(self.db_path).unlink(missing_ok=True)

    def test_heatmap_builds_nodes_and_edges(self) -> None:
        conversation_id = self.store.start_conversation()
        self.store.add_message(conversation_id, "user", "hello")
        self.store.log_tool_call(conversation_id, "web.search", {"query": "choiros"})
        self.store.log_file_write("docs/notes.md", b"content")

        snapshot = self.store.build_context_heatmap(limit=100)
        node_ids = {node["id"] for node in snapshot["nodes"]}
        node_types = {node["type"] for node in snapshot["nodes"]}

        self.assertIn("context-root", node_ids)
        self.assertIn("file:docs/notes.md", node_ids)
        self.assertIn("tool:web.search", node_ids)
        self.assertIn(f"conversation:{conversation_id}", node_ids)
        self.assertIn("message:user", node_ids)
        self.assertIn("file", node_types)

        edge_pairs = {(edge["source"], edge["target"]) for edge in snapshot["edges"]}
        self.assertIn((f"conversation:{conversation_id}", "tool:web.search"), edge_pairs)

    def test_heatmap_replay_honors_until_seq(self) -> None:
        conversation_id = self.store.start_conversation()
        self.store.add_message(conversation_id, "user", "first")
        seq_first = self.store.log_file_write("docs/alpha.md", b"alpha")

        seq_second = self.store.add_message(conversation_id, "assistant", "second")
        self.store.log_file_write("docs/beta.md", b"beta")

        snapshot = self.store.build_context_heatmap(until_seq=seq_first, limit=100)
        node_ids = {node["id"] for node in snapshot["nodes"]}

        self.assertIn("file:docs/alpha.md", node_ids)
        self.assertNotIn("file:docs/beta.md", node_ids)
        self.assertEqual(snapshot["until_seq"], seq_first)
        self.assertGreater(seq_second, seq_first)


if __name__ == "__main__":
    unittest.main()
