import json
import threading
import unittest
import urllib.parse
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
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        _SpritesHandler.received.append((self.path, self.headers, payload))

        if path == "/v1/sprites":
            self._send_json({"id": "sbx-1", "name": payload.get("name"), "url": "http://sprite-url"})
            return
        if path.endswith("/checkpoint") and path.startswith("/v1/sprites/"):
            body = "\n".join([
                json.dumps({"type": "progress", "data": "working"}),
                json.dumps({"type": "complete", "data": "Checkpoint v1 created"}),
            ])
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return
        if "/checkpoints/ckpt-1/restore" in path:
            body = json.dumps({"type": "complete", "data": "Restored to v1"})
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return
        if path.endswith("/exec") and path.startswith("/v1/sprites/"):
            self._send_json({"exit_code": 0, "stdout": "ok", "stderr": ""})
            return
        if path.endswith("/exec/proc-1/kill") and path.startswith("/v1/sprites/"):
            self._send_json({"ok": True})
            return
        self._send_json({"error": "not found"}, status=404)

    def do_DELETE(self) -> None:  # noqa: N802
        _SpritesHandler.received.append((self.path, self.headers, {}))
        if self.path.startswith("/v1/sprites/"):
            self._send_json({"ok": True})
            return
        self._send_json({"error": "not found"}, status=404)

    def do_GET(self) -> None:  # noqa: N802
        _SpritesHandler.received.append((self.path, self.headers, {}))
        if self.path.startswith("/v1/sprites/") and self.path.count("/") == 3:
            self._send_json({"url": "http://sprite-url"})
            return
        if self.path.endswith("/checkpoints") and self.path.startswith("/v1/sprites/"):
            self._send_json([{"id": "ckpt-1"}])
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
        cls.server.server_close()

    def setUp(self) -> None:
        _SpritesHandler.received.clear()

    def test_full_lifecycle(self) -> None:
        runner = SpritesSandboxRunner(api_base=f"http://127.0.0.1:{self.port}", token="token", use_ws_exec=False)
        config = SandboxConfig(
            user_id="u1",
            workspace_id="w1",
            workspace_root="/tmp",
            env={"TEST_ENV": "1"},
        )

        handle = runner.create(config)
        self.assertEqual(handle.sandbox_id, "w1")

        checkpoint = runner.checkpoint(handle, label="label")
        self.assertEqual(checkpoint.checkpoint_id, "ckpt-1")

        runner.restore(handle, checkpoint.checkpoint_id)
        result = runner.run(SandboxCommand(command=["echo", "ok"], sandbox=handle))
        self.assertEqual(result.return_code, 0)
        runner.stop_process(handle, "proc-1")
        proxy = runner.open_proxy(handle, 5173)
        self.assertEqual(proxy.url, "http://sprite-url")
        runner.destroy(handle)

        paths = [item[0] for item in _SpritesHandler.received]
        self.assertIn("/v1/sprites", paths)
        self.assertTrue(any(path.endswith("/checkpoint") for path in paths))
        self.assertTrue(any("/checkpoints/ckpt-1/restore" in path for path in paths))
        exec_paths = [path for path in paths if "/exec" in path and path.startswith("/v1/sprites/")]
        self.assertTrue(exec_paths)
        self.assertTrue(any(path.startswith("/v1/sprites/") and path.count("/") == 3 for path in paths))
        self.assertTrue(any(path.endswith("/exec/proc-1/kill") for path in paths))

        # Ensure auth header included
        headers = _SpritesHandler.received[0][1]
        self.assertEqual(headers.get("Authorization"), "Bearer token")

        def payloads_for(path: str) -> list[dict]:
            return [entry[2] for entry in _SpritesHandler.received if entry[0] == path]

        create_payload = payloads_for("/v1/sprites")[0]
        self.assertEqual(create_payload.get("name"), "w1")
        self.assertEqual(create_payload.get("url_settings", {}).get("auth"), "sprite")

        checkpoint_payload = payloads_for([path for path in paths if path.endswith("/checkpoint")][0])[0]
        self.assertEqual(checkpoint_payload.get("comment"), "label")

        exec_path = exec_paths[0]
        parsed = urllib.parse.urlparse(exec_path)
        query = urllib.parse.parse_qs(parsed.query)
        self.assertEqual(query.get("cmd"), ["echo", "ok"])

    def test_run_without_handle(self) -> None:
        runner = SpritesSandboxRunner(api_base=f"http://127.0.0.1:{self.port}")
        with self.assertRaises(SpritesAPIError):
            runner.run(SandboxCommand(command=["echo"]))
