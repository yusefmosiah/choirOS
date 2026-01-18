"""
Verifier runner (green thread).

Executes allowlisted verifier commands, stores raw output as artifacts,
produces structured reports and attestations. Optionally uses BAML for
LLM-powered analysis of command output.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VerifierSpec:
    verifier_id: str
    command: list[str]
    timeout_seconds: int = 300
    cwd: Optional[Path] = None
    env: Optional[dict[str, str]] = None


@dataclass(frozen=True)
class BamlAnalysis:
    """Structured analysis from BAML LLM call."""
    status: str  # PASS, FAIL, BLOCKER
    summary: str
    details: list[str]
    confidence: float
    analysis_hash: str


@dataclass(frozen=True)
class VerifierResult:
    verifier_id: str
    status: str
    return_code: int
    artifact_hash: str
    report_hash: str
    attestation_hash: str
    baml_analysis: Optional[BamlAnalysis] = None


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
        analyze_with_baml: bool = True,
    ) -> None:
        self.store = store or ArtifactStore()
        if sandbox_runner is None:
            from .sandbox_provider import get_sandbox_runner

            sandbox_runner = get_sandbox_runner()
        self.sandbox_runner = sandbox_runner
        self.sandbox_handle = sandbox_handle
        self.analyze_with_baml = analyze_with_baml

    def set_sandbox(self, handle: Optional[SandboxHandle]) -> None:
        self.sandbox_handle = handle

    async def _analyze_with_baml(
        self,
        command_str: str,
        exit_code: int,
        stdout: str,
        stderr: str,
    ) -> Optional[BamlAnalysis]:
        """Call BAML to analyze command output. Returns None on failure."""
        try:
            from .baml_client import b

            result = await b.AnalyzeVerifierOutput(
                command=command_str,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
            )

            # Store analysis as artifact
            analysis_payload = {
                "status": result.status,
                "summary": result.summary,
                "details": result.details,
                "confidence": result.confidence,
            }
            analysis_hash, _ = self.store.write_json(
                analysis_payload, suffix=".analysis.json"
            )

            return BamlAnalysis(
                status=result.status,
                summary=result.summary,
                details=list(result.details),
                confidence=result.confidence,
                analysis_hash=analysis_hash,
            )
        except Exception as e:
            logger.warning(f"BAML analysis failed: {e}")
            return None

    def run(self, spec: VerifierSpec) -> VerifierResult:
        """Synchronous run - wraps async version."""
        return asyncio.run(self.run_async(spec))

    async def run_async(self, spec: VerifierSpec) -> VerifierResult:
        """Execute verifier command and optionally analyze with BAML."""
        start = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        cwd = spec.cwd
        if self.sandbox_handle and self.sandbox_handle.config.workspace_root:
            workspace_root = Path(self.sandbox_handle.config.workspace_root)
            if cwd is None:
                cwd = workspace_root
            elif not cwd.is_absolute():
                cwd = workspace_root / cwd
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

        # BAML analysis (optional)
        baml_analysis: Optional[BamlAnalysis] = None
        if self.analyze_with_baml:
            command_str = " ".join(spec.command)
            baml_analysis = await self._analyze_with_baml(
                command_str, return_code, stdout, stderr
            )

        # Determine status: prefer BAML analysis if available
        if baml_analysis:
            status = baml_analysis.status.lower()
            if status not in ("pass", "fail", "blocker"):
                status = "pass" if return_code == 0 else "fail"
        else:
            status = "pass" if return_code == 0 else "fail"

        attestation = {
            "verifier_id": spec.verifier_id,
            "result": status,
            "artifact_hash": artifact_hash,
            "report_hash": report_hash,
            "command": spec.command,
            "started_at": start,
            "finished_at": end,
            "verifier_version": "v1",  # Bumped for BAML support
        }
        if baml_analysis:
            attestation["baml_analysis_hash"] = baml_analysis.analysis_hash
            attestation["baml_summary"] = baml_analysis.summary
            attestation["baml_confidence"] = baml_analysis.confidence
        attestation_hash, _ = self.store.write_json(attestation)

        return VerifierResult(
            verifier_id=spec.verifier_id,
            status=status,
            return_code=return_code,
            artifact_hash=artifact_hash,
            report_hash=report_hash,
            attestation_hash=attestation_hash,
            baml_analysis=baml_analysis,
        )


def default_python_command(args: list[str]) -> list[str]:
    return [sys.executable] + args


from .sandbox_runner import SandboxRunner, SandboxCommand, SandboxHandle
