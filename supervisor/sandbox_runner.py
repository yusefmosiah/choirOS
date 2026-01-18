"""Sandbox runner scaffolding (local runner by default)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class SandboxCommand:
    command: list[str]
    timeout_seconds: int = 300
    cwd: Optional[Path] = None
    env: Optional[dict[str, str]] = None
    sandbox: Optional["SandboxHandle"] = None


@dataclass(frozen=True)
class SandboxResources:
    cpu_cores: Optional[float] = None
    memory_mb: Optional[int] = None
    disk_mb: Optional[int] = None


@dataclass(frozen=True)
class SandboxNetworkPolicy:
    allow_internet: bool = True
    allowed_hosts: tuple[str, ...] = ()
    denied_hosts: tuple[str, ...] = ()


@dataclass(frozen=True)
class SandboxConfig:
    user_id: str
    workspace_id: str
    workspace_root: Optional[str] = None
    base_image: Optional[str] = None
    env: Optional[dict[str, str]] = None
    resources: Optional[SandboxResources] = None
    network_policy: Optional[SandboxNetworkPolicy] = None


@dataclass(frozen=True)
class SandboxHandle:
    sandbox_id: str
    config: SandboxConfig


@dataclass(frozen=True)
class SandboxCheckpoint:
    checkpoint_id: str
    created_at: str
    label: Optional[str] = None


@dataclass(frozen=True)
class SandboxResult:
    return_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


class SandboxRunner:
    def run(self, command: SandboxCommand) -> SandboxResult:
        raise NotImplementedError

    def create(self, config: SandboxConfig) -> SandboxHandle:
        raise NotImplementedError

    def destroy(self, handle: SandboxHandle) -> None:
        raise NotImplementedError

    def checkpoint(self, handle: SandboxHandle, label: Optional[str] = None) -> SandboxCheckpoint:
        raise NotImplementedError

    def restore(self, handle: SandboxHandle, checkpoint_id: str) -> None:
        raise NotImplementedError


class LocalSandboxRunner(SandboxRunner):
    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = root or (Path(".context") / "sandboxes")
        self.root.mkdir(parents=True, exist_ok=True)
        self._handles: dict[str, SandboxHandle] = {}

    def _sandbox_dir(self, handle: SandboxHandle) -> Path:
        return self.root / handle.sandbox_id

    def _checkpoint_path(self, handle: SandboxHandle) -> Path:
        return self._sandbox_dir(handle) / "checkpoints.json"

    def _load_checkpoints(self, handle: SandboxHandle) -> list[dict]:
        path = self._checkpoint_path(handle)
        if not path.exists():
            return []
        return json.loads(path.read_text() or "[]")

    def _save_checkpoints(self, handle: SandboxHandle, checkpoints: list[dict]) -> None:
        path = self._checkpoint_path(handle)
        path.write_text(json.dumps(checkpoints, indent=2))

    def create(self, config: SandboxConfig) -> SandboxHandle:
        sandbox_id = f"local-{uuid.uuid4().hex}"
        handle = SandboxHandle(sandbox_id=sandbox_id, config=config)
        sandbox_dir = self._sandbox_dir(handle)
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        (sandbox_dir / "config.json").write_text(json.dumps(asdict(config), indent=2))
        self._save_checkpoints(handle, [])
        self._handles[sandbox_id] = handle
        return handle

    def destroy(self, handle: SandboxHandle) -> None:
        sandbox_dir = self._sandbox_dir(handle)
        if sandbox_dir.exists():
            shutil.rmtree(sandbox_dir)
        self._handles.pop(handle.sandbox_id, None)

    def checkpoint(self, handle: SandboxHandle, label: Optional[str] = None) -> SandboxCheckpoint:
        checkpoint_id = f"ckpt-{uuid.uuid4().hex}"
        created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        record = {"id": checkpoint_id, "created_at": created_at, "label": label}
        checkpoints = self._load_checkpoints(handle)
        checkpoints.append(record)
        self._save_checkpoints(handle, checkpoints)
        return SandboxCheckpoint(checkpoint_id=checkpoint_id, created_at=created_at, label=label)

    def restore(self, handle: SandboxHandle, checkpoint_id: str) -> None:
        checkpoints = self._load_checkpoints(handle)
        if not any(item["id"] == checkpoint_id for item in checkpoints):
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")

    def run(self, command: SandboxCommand) -> SandboxResult:
        env = os.environ.copy()
        if command.env:
            env.update(command.env)

        cwd = command.cwd
        if cwd is None and command.sandbox and command.sandbox.config.workspace_root:
            cwd = Path(command.sandbox.config.workspace_root)

        try:
            completed = subprocess.run(
                command.command,
                cwd=str(cwd) if cwd else None,
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
