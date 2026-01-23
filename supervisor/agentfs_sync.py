"""AgentFS sync helpers."""

from __future__ import annotations

import asyncio
import os
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from agentfs_sdk.agentfs import AgentFS, AgentFSOptions
from agentfs_sdk.filesystem import Filesystem


DEFAULT_SEED_EXCLUDES = {
    ".agentfs",
    ".context",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "artifacts",
    "dist",
    "dist-ssr",
    "logs",
    "node_modules",
    "venv",
    ".venv",
}


def _session_id(user_id: str, workspace_id: Optional[str] = None) -> str:
    template = os.environ.get("CHOIR_AGENTFS_SESSION")
    if template:
        return template.format(user_id=user_id, workspace_id=workspace_id or "")
    return f"agentfs:{user_id}:workspace"


def _safe_session_id(session_id: str) -> str:
    return session_id.replace(":", "__").replace("/", "_")

def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _default_sandbox_root() -> Path:
    return Path(os.environ.get("CHOIR_SANDBOX_ROOT", ".context/sandboxes")).resolve()


def _should_skip(parts: Iterable[str], excludes: set[str]) -> bool:
    return any(part in excludes for part in parts)


def _run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, object] = {}
    error: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:
            error["error"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    if error:
        raise error["error"]
    return result.get("value")


async def _clear_root(fs: Filesystem) -> None:
    for name in await fs.readdir("/"):
        await fs.rm(f"/{name}", recursive=True, force=True)


async def _export_dir(fs: Filesystem, src: str, dest_root: Path) -> None:
    names = await fs.readdir(src)
    for name in names:
        child = f"{src.rstrip('/')}/{name}" if src != "/" else f"/{name}"
        stats = await fs.stat(child)
        rel = child.lstrip("/")
        dest = dest_root / rel
        if stats.is_directory():
            dest.mkdir(parents=True, exist_ok=True)
            await _export_dir(fs, child, dest_root)
        elif stats.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            data = await fs.read_file(child, encoding=None)
            if isinstance(data, str):
                dest.write_text(data)
            else:
                dest.write_bytes(data)


async def _import_dir(fs: Filesystem, src_root: Path, excludes: set[str]) -> None:
    for root, dirnames, filenames in os.walk(src_root):
        rel_dir = Path(root).relative_to(src_root)
        if rel_dir.parts and _should_skip(rel_dir.parts, excludes):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in excludes]
        if rel_dir.parts:
            await fs.mkdir("/" + rel_dir.as_posix())
        for name in filenames:
            rel_path = rel_dir / name if rel_dir.parts else Path(name)
            if _should_skip(rel_path.parts, excludes):
                continue
            file_path = Path(root) / name
            data = file_path.read_bytes()
            await fs.write_file("/" + rel_path.as_posix(), data)


@dataclass(frozen=True)
class AgentFSSync:
    root: Path
    sandbox_root: Optional[Path] = None

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        if self.sandbox_root is None:
            object.__setattr__(self, "sandbox_root", _default_sandbox_root())

    def _assert_safe_root(self, path: Path) -> None:
        root = (self.sandbox_root or _default_sandbox_root()).resolve()
        resolved = path.resolve()
        if not _is_relative_to(resolved, root):
            raise ValueError(f"Refusing to sync AgentFS outside sandbox root: {resolved}")

    def session_id(self, user_id: str, workspace_id: Optional[str]) -> str:
        return _session_id(user_id, workspace_id)

    def db_path(self, session_id: str) -> Path:
        return self.root / f"{_safe_session_id(session_id)}.db"

    def seed_if_empty(
        self,
        user_id: str,
        workspace_id: Optional[str],
        seed_root: Optional[Path],
        excludes: Optional[set[str]] = None,
    ) -> bool:
        if seed_root is None or not seed_root.exists():
            return False

        session_id = self.session_id(user_id, workspace_id)
        db_path = self.db_path(session_id)
        ignore = excludes or DEFAULT_SEED_EXCLUDES

        async def _seed() -> bool:
            agent = await AgentFS.open(
                AgentFSOptions(path=str(db_path), id=_safe_session_id(session_id))
            )
            async with agent:
                if await agent.fs.readdir("/"):
                    return False
                await _import_dir(agent.fs, seed_root, ignore)
                return True

        return bool(_run_async(_seed()))

    def sync_to_local(self, user_id: str, workspace_id: Optional[str], dest_root: Path) -> None:
        session_id = self.session_id(user_id, workspace_id)
        db_path = self.db_path(session_id)
        self._assert_safe_root(dest_root)

        async def _sync() -> None:
            agent = await AgentFS.open(
                AgentFSOptions(path=str(db_path), id=_safe_session_id(session_id))
            )
            async with agent:
                if dest_root.exists():
                    for entry in dest_root.iterdir():
                        if entry.is_dir():
                            shutil.rmtree(entry)
                        else:
                            entry.unlink()
                else:
                    dest_root.mkdir(parents=True, exist_ok=True)
                await _export_dir(agent.fs, "/", dest_root)

        _run_async(_sync())

    def sync_from_local(
        self,
        user_id: str,
        workspace_id: Optional[str],
        src_root: Path,
        excludes: Optional[set[str]] = None,
    ) -> None:
        session_id = self.session_id(user_id, workspace_id)
        db_path = self.db_path(session_id)
        self._assert_safe_root(src_root)
        ignore = excludes or DEFAULT_SEED_EXCLUDES

        async def _sync() -> None:
            agent = await AgentFS.open(
                AgentFSOptions(path=str(db_path), id=_safe_session_id(session_id))
            )
            async with agent:
                await _clear_root(agent.fs)
                await _import_dir(agent.fs, src_root, ignore)

        _run_async(_sync())
