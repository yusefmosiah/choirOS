"""
Verifier runner (green thread).

Executes allowlisted verifier commands, stores raw output as artifacts,
produces structured reports and attestations.
"""

from __future__ import annotations

import hashlib
import json
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
    def __init__(
        self,
        store: Optional[ArtifactStore] = None,
        sandbox_runner: Optional[SandboxRunner] = None,
        sandbox_handle: Optional[SandboxHandle] = None,
    ) -> None:
        self.store = store or ArtifactStore()
        if sandbox_runner is None:
            from .sandbox_provider import get_sandbox_runner

            sandbox_runner = get_sandbox_runner()
        self.sandbox_runner = sandbox_runner
        self.sandbox_handle = sandbox_handle

    def set_sandbox(self, handle: Optional[SandboxHandle]) -> None:
        self.sandbox_handle = handle

    def run(self, spec: VerifierSpec) -> VerifierResult:
        start = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        cwd = spec.cwd
        if self.sandbox_handle and self.sandbox_handle.config.workspace_root:
            cwd = Path(self.sandbox_handle.config.workspace_root)
        command = SandboxCommand(
            command=spec.command,
            timeout_seconds=spec.timeout_seconds,
            cwd=cwd,
            env=spec.env,
            sandbox=self.sandbox_handle,
        )
        result = self.sandbox_runner.run(command)
        return_code = result.return_code
        stdout = result.stdout or ""
        stderr = result.stderr or ""

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
from .sandbox_runner import SandboxRunner, SandboxCommand, SandboxHandle
