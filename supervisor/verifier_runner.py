"""
Verifier runner (green thread).

Executes allowlisted verifier commands, stores raw output as artifacts,
produces structured reports and attestations.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class VerifierSpec:
    verifier_id: str
    command: list[str]
    timeout_seconds: int = 300
    cwd: Optional[Path] = None
    env: Optional[dict[str, str]] = None


@dataclass(frozen=True)
class VerifierResult:
    verifier_id: str
    status: str
    return_code: int
    artifact_hash: str
    report_hash: str
    attestation_hash: str


class ArtifactStore:
    def __init__(self, root: Optional[Path] = None) -> None:
        if root is None:
            root = Path(".context") / "artifacts"
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def write_bytes(self, data: bytes, suffix: str) -> tuple[str, Path]:
        digest = hashlib.sha256(data).hexdigest()
        path = self.root / f"{digest}{suffix}"
        if not path.exists():
            path.write_bytes(data)
        return digest, path

    def write_json(self, payload: dict, suffix: str = ".json") -> tuple[str, Path]:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return self.write_bytes(encoded, suffix)


class VerifierRunner:
    def __init__(self, store: Optional[ArtifactStore] = None) -> None:
        self.store = store or ArtifactStore()

    def run(self, spec: VerifierSpec) -> VerifierResult:
        start = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        env = os.environ.copy()
        if spec.env:
            env.update(spec.env)

        try:
            completed = subprocess.run(
                spec.command,
                cwd=str(spec.cwd) if spec.cwd else None,
                env=env,
                capture_output=True,
                text=True,
                timeout=spec.timeout_seconds,
            )
            return_code = completed.returncode
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
        except subprocess.TimeoutExpired as exc:
            return_code = 124
            stdout = exc.stdout or ""
            stderr = (exc.stderr or "") + "\nTIMEOUT"

        end = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        raw_output = (
            "STDOUT\n" + stdout + "\nSTDERR\n" + stderr
        ).encode()
        artifact_hash, _ = self.store.write_bytes(raw_output, ".log")

        report = {
            "verifier_id": spec.verifier_id,
            "command": spec.command,
            "return_code": return_code,
            "artifact_hash": artifact_hash,
            "started_at": start,
            "finished_at": end,
        }
        report_hash, _ = self.store.write_json(report)

        status = "pass" if return_code == 0 else "fail"
        attestation = {
            "verifier_id": spec.verifier_id,
            "result": status,
            "artifact_hash": artifact_hash,
            "report_hash": report_hash,
            "command": spec.command,
            "started_at": start,
            "finished_at": end,
            "verifier_version": "v0",
        }
        attestation_hash, _ = self.store.write_json(attestation)

        return VerifierResult(
            verifier_id=spec.verifier_id,
            status=status,
            return_code=return_code,
            artifact_hash=artifact_hash,
            report_hash=report_hash,
            attestation_hash=attestation_hash,
        )


def default_python_command(args: list[str]) -> list[str]:
    return [sys.executable] + args
