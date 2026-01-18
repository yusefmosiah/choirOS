"""Sprites.dev sandbox adapter."""

from __future__ import annotations

import json
import os
import re
import threading
import asyncio
import urllib.error
import urllib.request
import urllib.parse
from dataclasses import asdict
from typing import Optional

from .sandbox_runner import (
    SandboxCheckpoint,
    SandboxCommand,
    SandboxConfig,
    SandboxHandle,
    SandboxProcess,
    SandboxProxy,
    SandboxResult,
    SandboxRunner,
)


class SpritesAPIError(RuntimeError):
    pass


DEFAULT_SPRITES_API_BASE = "https://api.sprites.dev"


class SpritesSandboxRunner(SandboxRunner):
    def __init__(
        self,
        api_base: str,
        token: Optional[str] = None,
        timeout_seconds: int = 60,
        use_ws_exec: Optional[bool] = None,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.use_ws_exec = (
            use_ws_exec if use_ws_exec is not None else os.environ.get("SPRITES_WS_EXEC", "1") == "1"
        )
        self._sprite_urls: dict[str, str] = {}

    @classmethod
    def from_env(cls) -> "SpritesSandboxRunner":
        api_base = os.environ.get("SPRITES_API_BASE") or os.environ.get("SPRITES_API_URL") or DEFAULT_SPRITES_API_BASE
        api_base = api_base.strip()
        token = (
            os.environ.get("SPRITES_API_TOKEN")
            or os.environ.get("SPRITES_TOKEN")
            or os.environ.get("SPRITE_TOKEN")
        )
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

    def _request_text(self, method: str, path: str, payload: Optional[dict] = None) -> str:
        url = f"{self.api_base}/{path.lstrip('/')}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method.upper())
        req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                return resp.read().decode("utf-8")
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

    @staticmethod
    def _extract_process_id(payload: dict) -> Optional[str]:
        return SpritesSandboxRunner._extract_id(payload, "process") or SpritesSandboxRunner._extract_id(
            payload,
            "exec",
        )

    @staticmethod
    def _extract_checkpoint_id(text: str) -> Optional[str]:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            data = payload.get("data")
            if isinstance(data, str):
                match = re.search(r"v\\d+", data)
                if match:
                    return match.group(0)
        return None

    def _sprite_name(self, handle: SandboxHandle | SandboxConfig) -> str:
        if isinstance(handle, SandboxHandle):
            return handle.config.workspace_id
        return handle.workspace_id

    def _build_exec_url(self, sprite: str, command: SandboxCommand) -> str:
        params: list[tuple[str, str]] = []
        for arg in command.command:
            params.append(("cmd", arg))
        if command.cwd:
            params.append(("dir", str(command.cwd)))
        if command.env:
            for key, value in command.env.items():
                params.append(("env", f"{key}={value}"))
        query = urllib.parse.urlencode(params, doseq=True)
        return f"{self.api_base}/v1/sprites/{sprite}/exec?{query}"

    def create(self, config: SandboxConfig) -> SandboxHandle:
        sprite_name = config.workspace_id
        auth_mode = os.environ.get("CHOIR_SPRITES_URL_AUTH", "sprite")
        payload = {"name": sprite_name, "url_settings": {"auth": auth_mode}}
        response = self._request("POST", "/v1/sprites", payload)
        sprite_url = response.get("url") or response.get("sprite_url") or response.get("endpoint")
        if isinstance(sprite_url, str):
            self._sprite_urls[sprite_name] = sprite_url
        return SandboxHandle(sandbox_id=sprite_name, config=config)

    def destroy(self, handle: SandboxHandle) -> None:
        sprite_name = self._sprite_name(handle)
        self._request("DELETE", f"/v1/sprites/{sprite_name}")

    def checkpoint(self, handle: SandboxHandle, label: Optional[str] = None) -> SandboxCheckpoint:
        sprite_name = self._sprite_name(handle)
        payload = {"comment": label} if label else {}
        text = self._request_text("POST", f"/v1/sprites/{sprite_name}/checkpoint", payload)
        checkpoint_id = self._extract_checkpoint_id(text)
        if not checkpoint_id:
            checkpoints = self._request("GET", f"/v1/sprites/{sprite_name}/checkpoints")
            if isinstance(checkpoints, list) and checkpoints:
                checkpoint_id = checkpoints[-1].get("id")
        if not checkpoint_id:
            raise SpritesAPIError("Sprites checkpoint did not return checkpoint id")
        return SandboxCheckpoint(checkpoint_id=checkpoint_id, created_at="", label=label)

    def restore(self, handle: SandboxHandle, checkpoint_id: str) -> None:
        sprite_name = self._sprite_name(handle)
        self._request_text("POST", f"/v1/sprites/{sprite_name}/checkpoints/{checkpoint_id}/restore")

    def run(self, command: SandboxCommand) -> SandboxResult:
        if not command.sandbox:
            raise SpritesAPIError("Sprites runner requires sandbox handle on SandboxCommand")
        sprite_name = self._sprite_name(command.sandbox)
        url = self._build_exec_url(sprite_name, command)
        req = urllib.request.Request(url, method="POST")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=command.timeout_seconds) as resp:
                body = resp.read().decode("utf-8")
            response = json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8") if exc.fp else str(exc)
            raise SpritesAPIError(f"Sprites exec error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise SpritesAPIError(f"Sprites exec failed: {exc}") from exc
        return SandboxResult(
            return_code=int(
                response.get("exit_code", response.get("return_code", response.get("code", 1)))
            ),
            stdout=str(response.get("stdout", "")),
            stderr=str(response.get("stderr", "")),
            timed_out=bool(response.get("timed_out", False)),
        )

    def start_process(self, command: SandboxCommand) -> SandboxProcess:
        if not command.sandbox:
            raise SpritesAPIError("Sprites runner requires sandbox handle on SandboxCommand")
        if not self.use_ws_exec:
            raise SpritesAPIError("Sprites background exec requires SPRITES_WS_EXEC=1")
        sprite_name = self._sprite_name(command.sandbox)
        params: list[tuple[str, str]] = []
        for arg in command.command:
            params.append(("cmd", arg))
        if command.cwd:
            params.append(("dir", str(command.cwd)))
        if command.env:
            for key, value in command.env.items():
                params.append(("env", f"{key}={value}"))
        max_run = os.environ.get("SPRITES_MAX_RUN_AFTER_DISCONNECT", "3600")
        params.append(("max_run_after_disconnect", max_run))
        params.append(("tty", "true"))
        query = urllib.parse.urlencode(params, doseq=True)
        ws_url = f"{self.api_base.replace('https://', 'wss://').replace('http://', 'ws://')}/v1/sprites/{sprite_name}/exec?{query}"

        async def _run_ws() -> str:
            import websockets  # type: ignore

            headers = []
            if self.token:
                headers.append(("Authorization", f"Bearer {self.token}"))
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                while True:
                    msg = await ws.recv()
                    if isinstance(msg, bytes):
                        continue
                    try:
                        data = json.loads(msg)
                    except json.JSONDecodeError:
                        continue
                    if data.get("type") == "session_info" and data.get("session_id"):
                        return str(data["session_id"])

        def _run_sync() -> str:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return asyncio.run(_run_ws())
            result: dict[str, str] = {}

            def _thread_runner() -> None:
                result["value"] = asyncio.run(_run_ws())

            thread = threading.Thread(target=_thread_runner, daemon=True)
            thread.start()
            thread.join(timeout=10)
            if "value" not in result:
                raise SpritesAPIError("Failed to start background exec session")
            return result["value"]

        session_id = _run_sync()
        return SandboxProcess(
            process_id=session_id,
            command=command.command,
            cwd=str(command.cwd) if command.cwd else None,
        )

    def stop_process(self, handle: SandboxHandle, process_id: str) -> None:
        sprite_name = self._sprite_name(handle)
        self._request("POST", f"/v1/sprites/{sprite_name}/exec/{process_id}/kill")

    def open_proxy(self, handle: SandboxHandle, port: int) -> SandboxProxy:
        sprite_name = self._sprite_name(handle)
        if sprite_name in self._sprite_urls:
            return SandboxProxy(url=self._sprite_urls[sprite_name], port=port)
        response = self._request("GET", f"/v1/sprites/{sprite_name}")
        url = response.get("url") or response.get("sprite_url") or response.get("endpoint")
        if not url:
            raise SpritesAPIError("Sprites sprite info did not return a URL")
        self._sprite_urls[sprite_name] = str(url)
        return SandboxProxy(url=str(url), port=port)
