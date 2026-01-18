"""Sandbox config helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .sandbox_runner import SandboxConfig, SandboxNetworkPolicy, SandboxResources


def _project_root() -> Path:
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        return Path(pythonpath.split(":")[0])
    return Path(__file__).parent.parent


def _read_int_env(key: str) -> Optional[int]:
    raw = os.environ.get(key)
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _read_float_env(key: str) -> Optional[float]:
    raw = os.environ.get(key)
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def build_sandbox_config(
    user_id: str,
    workspace_id: str,
    workspace_root: Optional[str] = None,
    env: Optional[dict[str, str]] = None,
    allow_internet: Optional[bool] = None,
    resources: Optional[SandboxResources] = None,
) -> SandboxConfig:
    root = workspace_root or os.environ.get(
        "CHOIR_SANDBOX_WORKSPACE_ROOT",
        str(_project_root()),
    )
    allow_internet_flag = allow_internet
    if allow_internet_flag is None:
        allow_internet_flag = os.environ.get("CHOIR_SANDBOX_ALLOW_INTERNET", "1") == "1"

    if resources is None:
        resources = SandboxResources(
            cpu_cores=_read_float_env("CHOIR_SANDBOX_CPU_CORES"),
            memory_mb=_read_int_env("CHOIR_SANDBOX_MEMORY_MB"),
            disk_mb=_read_int_env("CHOIR_SANDBOX_DISK_MB"),
        )

    env_payload = {"PYTHONPATH": str(_project_root())}
    if env:
        env_payload.update(env)

    return SandboxConfig(
        user_id=user_id,
        workspace_id=workspace_id,
        workspace_root=root,
        env=env_payload,
        resources=resources,
        network_policy=SandboxNetworkPolicy(allow_internet=allow_internet_flag),
    )
