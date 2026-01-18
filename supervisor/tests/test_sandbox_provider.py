import os
import unittest
from unittest import mock

from supervisor.sandbox_provider import get_sandbox_runner
from supervisor.sandbox_runner import LocalSandboxRunner


class TestSandboxProvider(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("CHOIR_SANDBOX_PROVIDER", None)

    def test_defaults_to_local(self) -> None:
        os.environ.pop("CHOIR_SANDBOX_PROVIDER", None)
        runner = get_sandbox_runner()
        self.assertIsInstance(runner, LocalSandboxRunner)

    def test_uses_sprites_runner(self) -> None:
        os.environ["CHOIR_SANDBOX_PROVIDER"] = "sprites"
        with mock.patch("supervisor.sprites_adapter.SpritesSandboxRunner.from_env") as mocked:
            mocked.return_value = mock.Mock()
            runner = get_sandbox_runner()
        self.assertEqual(runner, mocked.return_value)
