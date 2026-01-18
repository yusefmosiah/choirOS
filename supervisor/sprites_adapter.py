"""Sprites.dev sandbox adapter."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict
from typing import Optional

from .sandbox_runner import (
    SandboxCheckpoint,
    SandboxCommand,
    SandboxConfig,
    SandboxHandle,
    SandboxResult,
    SandboxRunner,
)


class SpritesAPIError(RuntimeError):
    pass


class SpritesSandboxRunner(SandboxRunner):
    def __init__(self, api_base: str, token: Optional[str] = None, timeout_seconds: int = 60) -> None:
        self.api_base = api_base.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> "SpritesSandboxRunner":
        api_base = os.environ.get("SPRITES_API_BASE", "").strip()
        if not api_base:
            raise SpritesAPIError("SPRITES_API_BASE is required for sprites adapter")
        token = os.environ.get("SPRITES_API_TOKEN")
        timeout = int(os.environ.get("SPRITES_API_TIMEOUT", "60"))
        return cls(api_base=api_base, token=token, timeout_seconds=timeout)

    def _request(self, method: str, path: str, payload: Optional[dict] = None) -> dict:
        url = f"{self.api_base}/{path.lstrip('/')}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method.upper())
        req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                body = resp.read()
                if not body:
                    return {}
                try:
                    return json.loads(body.decode("utf-8"))
                except json.JSONDecodeError:
                    return {"raw": body.decode("utf-8")}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8") if exc.fp else str(exc)
            raise SpritesAPIError(f"Sprites API error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise SpritesAPIError(f"Sprites API request failed: {exc}") from exc

    @staticmethod
    def _extract_id(payload: dict, key: str) -> Optional[str]:
        for candidate in (key, "id", f"{key}_id", f"{key}Id"):
            value = payload.get(candidate)
            if isinstance(value, str) and value:
                return value
        return None

    def create(self, config: SandboxConfig) -> SandboxHandle:
        payload = asdict(config)
        response = self._request("POST", "/v1/sandboxes", payload)
        sandbox_id = self._extract_id(response, "sandbox") or self._extract_id(response, "handle")
        if not sandbox_id:
            raise SpritesAPIError("Sprites create did not return sandbox id")
        return SandboxHandle(sandbox_id=sandbox_id, config=config)

    def destroy(self, handle: SandboxHandle) -> None:
        self._request("DELETE", f"/v1/sandboxes/{handle.sandbox_id}")

    def checkpoint(self, handle: SandboxHandle, label: Optional[str] = None) -> SandboxCheckpoint:
        payload = {"label": label} if label else {}
        response = self._request("POST", f"/v1/sandboxes/{handle.sandbox_id}/checkpoints", payload)
        checkpoint_id = self._extract_id(response, "checkpoint")
        created_at = response.get("created_at") or response.get("createdAt") or ""
        if not checkpoint_id:
            raise SpritesAPIError("Sprites checkpoint did not return checkpoint id")
        return SandboxCheckpoint(checkpoint_id=checkpoint_id, created_at=created_at or "", label=label)

    def restore(self, handle: SandboxHandle, checkpoint_id: str) -> None:
        payload = {"checkpoint_id": checkpoint_id}
        self._request("POST", f"/v1/sandboxes/{handle.sandbox_id}/restore", payload)

    def run(self, command: SandboxCommand) -> SandboxResult:
        if not command.sandbox:
            raise SpritesAPIError("Sprites runner requires sandbox handle on SandboxCommand")
        payload = {
            "command": command.command,
            "cwd": str(command.cwd) if command.cwd else None,
            "env": command.env or {},
            "timeout_seconds": command.timeout_seconds,
        }
        response = self._request("POST", f"/v1/sandboxes/{command.sandbox.sandbox_id}/exec", payload)
        return SandboxResult(
            return_code=int(response.get("return_code", response.get("exit_code", 1))),
            stdout=str(response.get("stdout", "")),
            stderr=str(response.get("stderr", "")),
            timed_out=bool(response.get("timed_out", False)),
        )
