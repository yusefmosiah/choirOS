import os
import unittest
from pathlib import Path
import uuid

from supervisor.sprites_adapter import SpritesSandboxRunner
from supervisor.sandbox_runner import SandboxCommand, SandboxConfig


def _load_env_file() -> None:
    env_path = Path(__file__).parent.parent.parent / "api" / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        cleaned = value.strip().strip("'").strip('"')
        os.environ.setdefault(key.strip(), cleaned)


class TestSpritesLive(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _load_env_file()

    def test_live_sprites_exec(self) -> None:
        token = (
            os.environ.get("SPRITES_API_TOKEN")
            or os.environ.get("SPRITES_TOKEN")
            or os.environ.get("SPRITE_TOKEN")
        )
        if not token:
            raise unittest.SkipTest("SPRITES_API_TOKEN not set; skipping live sprites test.")

        runner = SpritesSandboxRunner.from_env()
        sprite_name = f"choiros-live-{uuid.uuid4().hex[:8]}"
        config = SandboxConfig(user_id="local", workspace_id=sprite_name, workspace_root=".")
        handle = runner.create(config)
        checkpoint = None
        proxy = None
        try:
            result = runner.run(SandboxCommand(command=["echo", "ok"], sandbox=handle))
            checkpoint = runner.checkpoint(handle, label="live test")
            runner.restore(handle, checkpoint.checkpoint_id)
            proxy = runner.open_proxy(handle, 5173)
            if os.environ.get("SPRITES_WS_EXEC_LIVE", "0") == "1":
                process = runner.start_process(
                    SandboxCommand(command=["sleep", "1"], sandbox=handle)
                )
                runner.stop_process(handle, process.process_id)
        finally:
            runner.destroy(handle)
        self.assertEqual(result.return_code, 0)
        self.assertIn("ok", result.stdout)
        self.assertIsNotNone(checkpoint)
        self.assertTrue(checkpoint.checkpoint_id)
        self.assertIsNotNone(proxy)
        self.assertTrue(proxy.url)
