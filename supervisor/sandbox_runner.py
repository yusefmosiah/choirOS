"""Sandbox runner scaffolding (local runner by default)."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class SandboxCommand:
    command: list[str]
    timeout_seconds: int = 300
    cwd: Optional[Path] = None
    env: Optional[dict[str, str]] = None


@dataclass(frozen=True)
class SandboxResult:
    return_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


class SandboxRunner:
    def run(self, command: SandboxCommand) -> SandboxResult:
        raise NotImplementedError


class LocalSandboxRunner(SandboxRunner):
    def run(self, command: SandboxCommand) -> SandboxResult:
        env = os.environ.copy()
        if command.env:
            env.update(command.env)

        try:
            completed = subprocess.run(
                command.command,
                cwd=str(command.cwd) if command.cwd else None,
                env=env,
                capture_output=True,
                text=True,
                timeout=command.timeout_seconds,
            )
            return SandboxResult(
                return_code=completed.returncode,
                stdout=completed.stdout or "",
                stderr=completed.stderr or "",
                timed_out=False,
            )
        except subprocess.TimeoutExpired as exc:
            return SandboxResult(
                return_code=124,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + "\nTIMEOUT",
                timed_out=True,
            )
