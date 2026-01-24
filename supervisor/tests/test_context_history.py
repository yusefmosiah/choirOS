
import json
import unittest
from fastapi.testclient import TestClient
from supervisor.main import app
from supervisor.db import get_store

class TestContextHistory(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.store = get_store("test_user_ctx")
        # Clear existing events
        self.store.conn.execute("DELETE FROM events")
        self.store.conn.commit()

    def test_context_history_endpoint(self):
        # 1. Add some mock events
        self.store.append(
            "receipt.context.footprint",
            {
                "conversation_id": "conv-1",
                "mode": "CALM",
                "ahdb_state": {"key": "val"},
                "recent_files": ["foo.txt"],
                "recent_messages": [{"role": "user", "content": "hi"}]
            }
        )
        self.store.append(
            "receipt.context.footprint",
            {
                "conversation_id": "conv-1",
                "mode": "CALM",
                "ahdb_state": {"key": "val2"},
                "recent_files": ["bar.txt"],
                "recent_messages": [{"role": "assistant", "content": "hello"}]
            }
        )
        # Another conversation
        self.store.append(
            "receipt.context.footprint",
            {
                "conversation_id": "conv-2",
                "mode": "CODE",
                "ahdb_state": {},
            }
        )

        # 2. Query all
        resp = self.client.get("/context/history")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["history"]), 3)

        # 3. Query by conversation_id
        resp = self.client.get("/context/history?conversation_id=conv-1")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["history"]), 2)
        self.assertEqual(data["history"][0]["payload"]["recent_files"], ["foo.txt"])

if __name__ == "__main__":
    unittest.main()
