"""Sandbox provider selection."""

from __future__ import annotations

import os

from .sandbox_runner import LocalSandboxRunner, SandboxRunner


def get_sandbox_runner() -> SandboxRunner:
    provider = os.environ.get("CHOIR_SANDBOX_PROVIDER", "local").strip().lower()
    if provider in {"sprites", "sprites.dev", "spritesdev"}:
        from .sprites_adapter import SpritesSandboxRunner

        return SpritesSandboxRunner.from_env()
    return LocalSandboxRunner()
