import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from supervisor.sprites_adapter import SpritesSandboxRunner, SpritesAPIError
from supervisor.sandbox_runner import SandboxCommand, SandboxConfig


class _SpritesHandler(BaseHTTPRequestHandler):
    received = []

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        data = self.rfile.read(length)
        return json.loads(data.decode("utf-8"))

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        payload = self._read_body()
        _SpritesHandler.received.append((self.path, self.headers, payload))

        if self.path == "/sandboxes":
            self._send_json({"sandbox_id": "sbx-1"})
            return
        if self.path == "/sandboxes/sbx-1/checkpoints":
            self._send_json({"checkpoint_id": "ckpt-1", "created_at": "now"})
            return
        if self.path == "/sandboxes/sbx-1/restore":
            self._send_json({"ok": True})
            return
        if self.path == "/sandboxes/sbx-1/exec":
            self._send_json({"return_code": 0, "stdout": "ok", "stderr": ""})
            return
        self._send_json({"error": "not found"}, status=404)

    def do_DELETE(self) -> None:  # noqa: N802
        _SpritesHandler.received.append((self.path, self.headers, {}))
        if self.path == "/sandboxes/sbx-1":
            self._send_json({"ok": True})
            return
        self._send_json({"error": "not found"}, status=404)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class TestSpritesAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = HTTPServer(("127.0.0.1", 0), _SpritesHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.thread.join()

    def setUp(self) -> None:
        _SpritesHandler.received.clear()

    def test_full_lifecycle(self) -> None:
        runner = SpritesSandboxRunner(api_base=f"http://127.0.0.1:{self.port}", token="token")
        config = SandboxConfig(user_id="u1", workspace_id="w1", workspace_root="/tmp")

        handle = runner.create(config)
        self.assertEqual(handle.sandbox_id, "sbx-1")

        checkpoint = runner.checkpoint(handle, label="label")
        self.assertEqual(checkpoint.checkpoint_id, "ckpt-1")

        runner.restore(handle, checkpoint.checkpoint_id)
        result = runner.run(SandboxCommand(command=["echo", "ok"], sandbox=handle))
        self.assertEqual(result.return_code, 0)
        runner.destroy(handle)

        paths = [item[0] for item in _SpritesHandler.received]
        self.assertIn("/sandboxes", paths)
        self.assertIn("/sandboxes/sbx-1/checkpoints", paths)
        self.assertIn("/sandboxes/sbx-1/restore", paths)
        self.assertIn("/sandboxes/sbx-1/exec", paths)
        self.assertIn("/sandboxes/sbx-1", paths)

        # Ensure auth header included
        headers = _SpritesHandler.received[0][1]
        self.assertEqual(headers.get("Authorization"), "Bearer token")

    def test_run_without_handle(self) -> None:
        runner = SpritesSandboxRunner(api_base=f"http://127.0.0.1:{self.port}")
        with self.assertRaises(SpritesAPIError):
            runner.run(SandboxCommand(command=["echo"]))
