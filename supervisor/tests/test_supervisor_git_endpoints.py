import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from supervisor.db import EventStore
from supervisor import main as supervisor_main


class TestSupervisorGitEndpoints(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["NATS_ENABLED"] = "0"
        fd, self.db_path = tempfile.mkstemp(prefix="choiros_api_", suffix=".sqlite")
        os.close(fd)
        self.store = EventStore(db_path=Path(self.db_path), user_id="local")
        self.client = TestClient(supervisor_main.app)

    def tearDown(self) -> None:
        self.store.close()
        Path(self.db_path).unlink(missing_ok=True)

    def test_git_last_good_empty(self) -> None:
        with mock.patch("supervisor.main.get_store", return_value=self.store):
            response = self.client.get("/git/last_good")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json().get("last_good"))

    def test_git_rollback_missing_last_good(self) -> None:
        with mock.patch("supervisor.main.get_store", return_value=self.store):
            response = self.client.post("/git/rollback?dry_run=false")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload.get("success"))
        self.assertEqual(payload.get("error"), "No last_good_checkpoint set")

    def test_git_rollback_success(self) -> None:
        self.store.set_last_good_checkpoint("deadbeef")
        with (
            mock.patch("supervisor.main.get_store", return_value=self.store),
            mock.patch("supervisor.git_ops.git_revert", return_value={"success": True}),
        ):
            response = self.client.post("/git/rollback?dry_run=false")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("success"))
        self.assertEqual(payload.get("last_good"), "deadbeef")

    def test_git_diff_endpoint(self) -> None:
        expected = {"success": True, "base": "a", "head": "b", "diff": "ok"}
        with mock.patch("supervisor.git_ops.diff_between", return_value=expected):
            response = self.client.get("/git/diff?base=a&head=b&stat=true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
