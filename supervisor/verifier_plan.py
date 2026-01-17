"""
Verifier plan selection.

Loads allowlisted verifiers and selects a plan by mood + touched paths.
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Optional
import shlex

from .verifier_runner import VerifierSpec


def _project_root() -> Path:
    return Path(__file__).parent.parent


@dataclass(frozen=True)
class VerifierPlan:
    plan_id: str
    inputs_hash: str
    verifier_ids: list[str]
    unknown_required: list[str]

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "inputs_hash": self.inputs_hash,
            "verifier_ids": self.verifier_ids,
            "unknown_required": self.unknown_required,
        }


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _load_config(path: Optional[Path] = None) -> dict:
    config_path = path or (_project_root() / "config" / "verifiers.yaml")
    text = config_path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
    except Exception:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Invalid verifier config format")
    return data


def get_verifier_config(path: Optional[Path] = None) -> dict:
    return _load_config(path)


def build_verifier_specs(verifier_ids: list[str], config_path: Optional[Path] = None) -> list[VerifierSpec]:
    config = _load_config(config_path)
    by_id = {v.get("id"): v for v in config.get("verifiers", []) if v.get("id")}
    specs: list[VerifierSpec] = []
    repo_root = _project_root()
    for verifier_id in verifier_ids:
        entry = by_id.get(verifier_id)
        if not entry:
            continue
        command_str = entry.get("command", "")
        if not command_str:
            continue
        command = shlex.split(command_str)
        specs.append(VerifierSpec(verifier_id=verifier_id, command=command, cwd=repo_root))
    return specs


def _matches_scope(touched: list[str], scopes: list[str]) -> bool:
    if not scopes:
        return False
    normalized = [_normalize_path(path) for path in touched]
    for scope in scopes:
        scope_norm = _normalize_path(scope)
        if scope_norm.endswith("/"):
            prefix = scope_norm
            if any(path.startswith(prefix) for path in normalized):
                return True
            continue
        if any(fnmatch(path, scope_norm) for path in normalized):
            return True
    return False


def _hash_inputs(data: dict) -> str:
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def select_verifier_plan(
    touched_paths: list[str],
    mood: Optional[str],
    required_verifiers: Optional[list[str]] = None,
    risk_tier: Optional[str] = None,
    config_path: Optional[Path] = None,
) -> VerifierPlan:
    config = _load_config(config_path)
    verifiers = config.get("verifiers", [])
    mood_defaults = config.get("mood_defaults", {})

    mood_key = (mood or "").upper()
    required = required_verifiers or []

    selected: set[str] = set()
    unknown_required: list[str] = []

    # Always include required verifiers if known.
    verifier_index = {v.get("id"): v for v in verifiers if v.get("id")}
    for verifier_id in required:
        if verifier_id in verifier_index:
            selected.add(verifier_id)
        else:
            unknown_required.append(verifier_id)

    # Add mood defaults.
    for verifier_id in mood_defaults.get(mood_key, []):
        if verifier_id in verifier_index:
            selected.add(verifier_id)

    # Add scope-based verifiers for touched paths.
    for verifier in verifiers:
        verifier_id = verifier.get("id")
        if not verifier_id:
            continue
        moods = [m.upper() for m in verifier.get("moods", []) if isinstance(m, str)]
        scopes = verifier.get("scopes", [])
        if moods and mood_key and mood_key not in moods:
            continue
        if _matches_scope(touched_paths, scopes):
            selected.add(verifier_id)

    verifier_ids = sorted(selected)

    inputs = {
        "touched_paths": sorted({_normalize_path(p) for p in touched_paths}),
        "mood": mood_key or None,
        "required_verifiers": sorted(required),
        "risk_tier": risk_tier,
        "verifier_ids": verifier_ids,
        "unknown_required": sorted(unknown_required),
    }
    inputs_hash = _hash_inputs(inputs)
    plan_id = hashlib.sha256(f"plan:{inputs_hash}".encode()).hexdigest()

    return VerifierPlan(
        plan_id=plan_id,
        inputs_hash=inputs_hash,
        verifier_ids=verifier_ids,
        unknown_required=sorted(unknown_required),
    )
