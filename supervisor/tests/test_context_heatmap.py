import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from supervisor.db import ProjectionStore


class TestContextHeatmap(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.db_path = tempfile.mkstemp(prefix="choiros_heatmap_", suffix=".sqlite")
        os.close(fd)
        self.store = ProjectionStore(
            db_path=Path(self.db_path),
            user_id="local",
        )

    def tearDown(self) -> None:
        self.store.close()
        Path(self.db_path).unlink(missing_ok=True)

    def test_heatmap_builds_nodes_and_edges(self) -> None:
        conversation_id = 1001
        now = int(datetime.now().timestamp() * 1000)
        self.store.apply_event(
            "message",
            {"conversation_id": conversation_id, "role": "user", "content": "hello"},
            now,
        )
        self.store.apply_event(
            "tool.call",
            {"conversation_id": conversation_id, "tool_name": "web.search", "tool_input": {"query": "choiros"}},
            now,
        )
        self.store.apply_event(
            "file.write",
            {"path": "docs/notes.md", "content_hash": "content"},
            now,
        )
        self.store.conn.commit()

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
        conversation_id = 2002
        now = int(datetime.now().timestamp() * 1000)
        self.store.apply_event(
            "message",
            {"conversation_id": conversation_id, "role": "user", "content": "first"},
            now,
        )
        seq_first = self.store.apply_event(
            "file.write",
            {"path": "docs/alpha.md", "content_hash": "alpha"},
            now,
        )

        seq_second = self.store.apply_event(
            "message",
            {"conversation_id": conversation_id, "role": "assistant", "content": "second"},
            now,
        )
        self.store.apply_event(
            "file.write",
            {"path": "docs/beta.md", "content_hash": "beta"},
            now,
        )
        self.store.conn.commit()

        snapshot = self.store.build_context_heatmap(until_seq=seq_first, limit=100)
        node_ids = {node["id"] for node in snapshot["nodes"]}

        self.assertIn("file:docs/alpha.md", node_ids)
        self.assertNotIn("file:docs/beta.md", node_ids)
        self.assertEqual(snapshot["until_seq"], seq_first)
        self.assertGreater(seq_second, seq_first)


if __name__ == "__main__":
    unittest.main()
