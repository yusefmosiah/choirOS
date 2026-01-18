import os
import unittest
from pathlib import Path

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
        os.environ.setdefault(key.strip(), value.strip())


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
        config = SandboxConfig(user_id="local", workspace_id="choiros-live", workspace_root=".")
        handle = runner.create(config)
        result = runner.run(SandboxCommand(command=["echo", "ok"], sandbox=handle))
        runner.destroy(handle)
        self.assertEqual(result.return_code, 0)
