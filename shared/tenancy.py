"""NATS tenancy scaffolding (user_id -> subject prefix)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class TenantConfig:
    user_id: str
    subject_prefix: str


@dataclass(frozen=True)
class NatsCredentials:
    user: str
    password: str
    subject_prefix: str
    role: str


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _config_path() -> Path:
    raw = os.environ.get("CHOIROS_TENANCY_CONFIG")
    if raw:
        return Path(raw)
    return _project_root() / "config" / "tenancy.json"


def load_tenancy_config() -> dict:
    path = _config_path()
    if not path.exists():
        return {"default_user_id": "local", "tenants": {}}
    return json.loads(path.read_text())


def get_default_user_id() -> str:
    config = load_tenancy_config()
    return config.get("default_user_id", "local")


def get_tenant(user_id: str) -> Optional[TenantConfig]:
    config = load_tenancy_config()
    tenants = config.get("tenants", {})
    entry = tenants.get(user_id)
    if not entry:
        return None
    return TenantConfig(user_id=user_id, subject_prefix=entry.get("subject_prefix", ""))


def get_nats_ws_url() -> str:
    env = os.environ.get("NATS_WS_URL")
    if env:
        return env
    config = load_tenancy_config()
    nats_config = config.get("nats", {}) if isinstance(config, dict) else {}
    return nats_config.get("ws_url", "ws://localhost:8080")


def get_nats_credentials(user_id: str, role: str = "web") -> Optional[NatsCredentials]:
    config = load_tenancy_config()
    tenant = (config.get("tenants") or {}).get(user_id)
    if not tenant:
        return None
    subject_prefix = tenant.get("subject_prefix", f"choiros.{user_id}.>")
    nats_entry = (tenant.get("nats") or {}).get(role)
    if not nats_entry:
        return None
    user = nats_entry.get("user")
    password = nats_entry.get("password")
    if not user or not password:
        return None
    return NatsCredentials(user=user, password=password, subject_prefix=subject_prefix, role=role)


def get_supervisor_nats_credentials() -> Optional[NatsCredentials]:
    config = load_tenancy_config()
    supervisor = (config.get("supervisor") or {}).get("nats") if isinstance(config, dict) else None
    if not supervisor:
        return None
    user = supervisor.get("user")
    password = supervisor.get("password")
    if not user or not password:
        return None
    return NatsCredentials(user=user, password=password, subject_prefix="choiros.>", role="supervisor")


def subject_prefix_for(user_id: str) -> str:
    tenant = get_tenant(user_id)
    if tenant and tenant.subject_prefix:
        return tenant.subject_prefix
    return f"choiros.{user_id}.>"
