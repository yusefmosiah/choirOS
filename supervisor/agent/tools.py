"""
Agent Tools - The 4 minimal tools for the ChoirOS agent.

Based on AGENT_TOOLS.md:
- read_file: Read file contents with optional head/tail
- write_file: Create or overwrite file
- edit_file: Text-match replace with dry_run option
- bash: Execute shell command
- git_checkpoint: Create a git commit as a save point
- git_status: Check git status and recent commits
"""

import asyncio
import os
import uuid
from pathlib import Path
from typing import Any, Optional
import difflib

from ..event_publisher import EventPublisher, get_publisher
from .web_search import WebSearch
from ..mode_config import ModeConfig
from ..verifier_runner import ArtifactStore


# Detect project root - use PYTHONPATH if set, otherwise find relative to this file
def _get_project_root() -> Path:
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        return Path(pythonpath.split(":")[0])
    # Fall back to 3 levels up from this file (supervisor/agent/tools.py -> project root)
    return Path(__file__).parent.parent.parent


PROJECT_ROOT = _get_project_root()
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


class AgentTools:
    """Implementation of the 5 agent tools."""

    def __init__(
        self,
        file_history=None,
        event_publisher: Optional[EventPublisher] = None,
        mode_config: Optional[ModeConfig] = None,
    ):
        """
        Initialize tools.

        Args:
            file_history: Optional FileHistory instance for undo support
            event_publisher: Optional EventPublisher for logging events
        """
        self.file_history = file_history
        self.publisher = event_publisher or get_publisher()
        self.mode_config = mode_config
        self.env = os.environ.copy()
        self.cwd = str(PROJECT_ROOT / "choiros")  # Default working directory
        self.app_dir = PROJECT_ROOT
        self.web_search = WebSearch()
        self.artifacts = ArtifactStore(event_publisher=self.publisher)
        self.current_run_id: Optional[str] = None

    # Tool definitions for Claude
    TOOL_DEFINITIONS = [
        {
            "name": "read_file",
            "description": "Read file contents. Use head/tail for large files.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read (relative to /app or absolute)"
                    },
                    "head": {
                        "type": "integer",
                        "description": "Optional: Return only the first N lines"
                    },
                    "tail": {
                        "type": "integer",
                        "description": "Optional: Return only the last N lines"
                    }
                },
                "required": ["path"]
            }
        },
        {
            "name": "write_file",
            "description": "Create or overwrite file with content.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to write (relative to /app or absolute)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["path", "content"]
            }
        },
        {
            "name": "edit_file",
            "description": "Replace exact text matches in a file. Returns diff.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to edit"
                    },
                    "edits": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "old_text": {"type": "string"},
                                "new_text": {"type": "string"}
                            },
                            "required": ["old_text", "new_text"]
                        },
                        "description": "List of text replacements to make"
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "If true, show what would change without making changes",
                        "default": False
                    }
                },
                "required": ["path", "edits"]
            }
        },
        {
            "name": "bash",
            "description": "Execute shell command. Output streamed to file.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default 300)",
                        "default": 300
                    }
                },
                "required": ["command"]
            }
        },
        {
            "name": "git_checkpoint",
            "description": "Create a git commit as a save point. Use before making risky changes.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Commit message describing the checkpoint"
                    }
                },
                "required": []
            }
        },
        {
            "name": "git_status",
            "description": "Get git status and recent commit history.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "log_count": {
                        "type": "integer",
                        "description": "Number of recent commits to show (default 5)",
                        "default": 5
                    }
                },
                "required": []
            }
        },
        {
            "name": "web_search",
            "description": "Search the web for information using Tavily.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max links to return (default 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "read_artifact",
            "description": "Read artifact content by hash.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "artifact_hash": {
                        "type": "string",
                        "description": "Content hash of the artifact"
                    },
                    "max_bytes": {
                        "type": "integer",
                        "description": "Max bytes to return (default 2000)",
                        "default": 2000
                    }
                },
                "required": ["artifact_hash"]
            }
        },
        {
            "name": "propose_ahdb",
            "description": "Propose an update to the AHDB (Authentically Horizontal Data Base). Requires verification.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "field": {
                        "type": "string",
                        "description": "The state field to update (e.g., 'user.email')"
                    },
                    "value": {
                        "type": "object",
                        "description": "The new value for the field (JSON object)"
                    },
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of evidence strings (e.g. filenames, URLs) supporting this proposal"
                    }
                },
                "required": ["field", "value", "evidence"]
            }
        }
    ]

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to app_dir if not absolute."""
        p = Path(path)
        if not p.is_absolute():
            p = self.app_dir / path
        resolved = p.resolve()
        root = self.app_dir.resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            raise ValueError(f"Path outside workspace: {path}")
        return resolved

    def _display_path(self, path: Path) -> str:
        """Prefer app-relative paths for event payloads."""
        try:
            return str(path.relative_to(self.app_dir))
        except ValueError:
            return str(path)

    async def _emit_artifact_pointer(self, artifact_hash: str, path: str, kind: str, size_bytes: int) -> None:
        if not self.publisher:
            return
        payload = {
            "artifact_hash": artifact_hash,
            "path": path,
            "kind": kind,
            "size_bytes": size_bytes,
        }
        if self.current_run_id:
            payload["run_id"] = self.current_run_id
        await self.publisher.publish(
            "artifact.pointer",
            payload,
            source="system",
        )

    def _assert_tool_allowed(self, tool_name: str, requires_write: bool = False, requires_network: bool = False) -> Optional[dict[str, Any]]:
        if not self.mode_config:
            return None
        if not self.mode_config.allows_tool(tool_name):
            return {"error": f"Tool not allowed in mode {self.mode_config.mode_id}: {tool_name}"}
        if requires_write and not self.mode_config.allow_write:
            return {"error": f"Write access denied in mode {self.mode_config.mode_id}"}
        if requires_network and not self.mode_config.allow_network:
            return {"error": f"Network access denied in mode {self.mode_config.mode_id}"}
        return None

    async def read_file(self, path: str, head: int | None = None, tail: int | None = None) -> dict[str, Any]:
        """Read file contents."""
        denial = self._assert_tool_allowed("read_file")
        if denial:
            return denial
        try:
            file_path = self._resolve_path(path)

            if not file_path.exists():
                return {"error": f"File not found: {path}"}

            if not file_path.is_file():
                return {"error": f"Not a file: {path}"}

            content = file_path.read_text()
            lines = content.splitlines()

            if head is not None:
                lines = lines[:head]
            elif tail is not None:
                lines = lines[-tail:]

            result = {
                "content": "\n".join(lines),
                "total_lines": len(content.splitlines()),
                "returned_lines": len(lines),
            }
            if self.publisher:
                payload = {
                    "path": self._display_path(file_path),
                    "bytes": len(content.encode()),
                    "head": head,
                    "tail": tail,
                }
                if self.current_run_id:
                    payload["run_id"] = self.current_run_id
                await self.publisher.publish(
                    "receipt.read",
                    payload,
                    source="agent",
                )
            return result

        except Exception as e:
            return {"error": str(e)}

    async def write_file(self, path: str, content: str) -> dict[str, Any]:
        """Write content to a file."""
        denial = self._assert_tool_allowed("write_file", requires_write=True)
        if denial:
            return denial
        try:
            file_path = self._resolve_path(path)
            original = file_path.read_text() if file_path.exists() else ""

            # Save state for undo before writing
            if self.file_history:
                await self.file_history.save_state(str(file_path))

            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            file_path.write_text(content)

            if self.publisher:
                await self.publisher.log_file_write_async(
                    self._display_path(file_path),
                    content.encode(),
                    run_id=self.current_run_id,
                )
            diff = "\n".join(
                difflib.unified_diff(
                    original.splitlines(),
                    content.splitlines(),
                    fromfile=self._display_path(file_path),
                    tofile=self._display_path(file_path),
                    lineterm="",
                )
            )
            if diff:
                artifact_hash, _ = await self.artifacts.write_bytes(diff.encode(), ".diff")
                await self._emit_artifact_pointer(
                    artifact_hash,
                    self._display_path(file_path),
                    "diff",
                    len(diff.encode()),
                )

            result = {
                "success": True,
                "path": str(file_path),
                "bytes_written": len(content.encode()),
            }
            if self.publisher:
                payload = {
                    "path": self._display_path(file_path),
                    "bytes": len(content.encode()),
                    "action": "write",
                }
                if self.current_run_id:
                    payload["run_id"] = self.current_run_id
                await self.publisher.publish(
                    "receipt.patch",
                    payload,
                    source="agent",
                )
            return result

        except Exception as e:
            return {"error": str(e)}

    async def edit_file(
        self,
        path: str,
        edits: list[dict[str, str]],
        dry_run: bool = False
    ) -> dict[str, Any]:
        """Apply text replacements to a file."""
        denial = self._assert_tool_allowed("edit_file", requires_write=True)
        if denial:
            return denial
        try:
            file_path = self._resolve_path(path)

            if not file_path.exists():
                return {"error": f"File not found: {path}"}

            content = file_path.read_text()
            original = content
            changes = []

            for edit in edits:
                old_text = edit["old_text"]
                new_text = edit["new_text"]

                if old_text not in content:
                    changes.append({
                        "old_text": old_text[:50] + "..." if len(old_text) > 50 else old_text,
                        "status": "not_found"
                    })
                    continue

                # Count occurrences
                count = content.count(old_text)
                content = content.replace(old_text, new_text)

                changes.append({
                    "old_text": old_text[:50] + "..." if len(old_text) > 50 else old_text,
                    "new_text": new_text[:50] + "..." if len(new_text) > 50 else new_text,
                    "occurrences": count,
                    "status": "replaced"
                })

            if dry_run:
                return {
                    "dry_run": True,
                    "changes": changes,
                    "would_modify": content != original,
                }

            if content != original:
                # Save state for undo before writing
                if self.file_history:
                    await self.file_history.save_state(str(file_path))

                file_path.write_text(content)
                if self.publisher:
                    await self.publisher.log_file_write_async(
                        self._display_path(file_path),
                        content.encode(),
                        run_id=self.current_run_id,
                    )
                diff = "\n".join(
                    difflib.unified_diff(
                        original.splitlines(),
                        content.splitlines(),
                        fromfile=self._display_path(file_path),
                        tofile=self._display_path(file_path),
                        lineterm="",
                    )
                )
                if diff:
                    artifact_hash, _ = await self.artifacts.write_bytes(diff.encode(), ".diff")
                    await self._emit_artifact_pointer(
                        artifact_hash,
                        self._display_path(file_path),
                        "diff",
                        len(diff.encode()),
                    )

            result = {
                "success": True,
                "path": str(file_path),
                "changes": changes,
                "modified": content != original,
            }
            if result.get("modified") and self.publisher:
                payload = {
                    "path": self._display_path(file_path),
                    "bytes": len(content.encode()),
                    "action": "edit",
                }
                if self.current_run_id:
                    payload["run_id"] = self.current_run_id
                await self.publisher.publish(
                    "receipt.patch",
                    payload,
                    source="agent",
                )
            return result

        except Exception as e:
            return {"error": str(e)}

    async def bash(self, command: str, timeout: int = 300) -> dict[str, Any]:
        """Execute a shell command."""
        denial = self._assert_tool_allowed("bash")
        if denial:
            return denial
        try:
            cmd_id = str(uuid.uuid4())[:8]
            log_path = LOG_DIR / f"cmd_{cmd_id}.txt"

            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=self.cwd,
                env=self.env,
            )

            # Stream output to file
            output_lines = []
            stdout = proc.stdout
            if stdout is None:
                raise RuntimeError("Process stdout not available")
            with open(log_path, "w") as f:
                try:
                    async def read_output():
                        async for line in stdout:
                            decoded = line.decode()
                            f.write(decoded)
                            output_lines.append(decoded)

                    await asyncio.wait_for(read_output(), timeout=timeout)
                except asyncio.TimeoutError:
                    proc.kill()
                    f.write("\n[TIMEOUT - process killed]\n")
                    output_lines.append("\n[TIMEOUT - process killed]\n")

            await proc.wait()

            content = "".join(output_lines)
            preview = content[:500]
            artifact_hash = None
            if log_path.exists():
                artifact_hash, _ = await self.artifacts.write_bytes(log_path.read_bytes(), ".log")
                await self._emit_artifact_pointer(
                    artifact_hash,
                    str(log_path),
                    "bash.log",
                    log_path.stat().st_size,
                )

            return {
                "exit_code": proc.returncode,
                "output_file": str(log_path),
                "output_preview": preview,
                "truncated": len(content) > 500,
                "artifact_hash": artifact_hash,
            }

        except Exception as e:
            return {"error": str(e)}

    async def read_artifact(self, artifact_hash: str, max_bytes: int = 2000) -> dict[str, Any]:
        """Read artifact content by hash."""
        denial = self._assert_tool_allowed("read_artifact")
        if denial:
            return denial
        try:
            candidates = sorted(self.artifacts.root.glob(f"{artifact_hash}*"))
            if not candidates:
                return {"error": f"Artifact not found: {artifact_hash}"}
            path = candidates[0]
            data = path.read_bytes()
            truncated = len(data) > max_bytes
            content = data[:max_bytes].decode(errors="replace")
            if self.publisher:
                payload = {
                    "artifact_hash": artifact_hash,
                    "path": str(path),
                    "bytes": len(data),
                }
                if self.current_run_id:
                    payload["run_id"] = self.current_run_id
                await self.publisher.publish(
                    "receipt.read",
                    payload,
                    source="agent",
                )
            return {"content": content, "bytes": len(data), "truncated": truncated}
        except Exception as e:
            return {"error": str(e)}

    async def propose_ahdb(self, field: str, value: dict[str, Any], evidence: list[str]) -> dict[str, Any]:
        """Propose an AHDB update (ASSERT/HYPOTHESIZE/DRIVE/BELIEVE)."""
        denial = self._assert_tool_allowed("propose_ahdb")
        if denial:
            return denial
        
        if not self.current_run_id:
            return {"error": "No active run ID found (internal error)"}
            
        try:
            if not self.publisher:
                return {"error": "No event publisher connected"}

            await self.publisher.publish(
                "receipt.ahdb.delta",
                {
                    "delta": {field: value},
                    "authority": "proposed",
                    "evidence": evidence,
                    "run_id": self.current_run_id,
                },
                source="system",
            )
            return {
                "status": "proposed",
                "field": field,
                "note": "This proposal will be verified by the system before being asserted."
            }
        except Exception as e:
            return {"error": str(e)}

    async def git_checkpoint(self, message: Optional[str] = None) -> dict[str, Any]:
        """Create a git checkpoint."""
        denial = self._assert_tool_allowed("git_checkpoint")
        if denial:
            return denial
        try:
            from ..git_ops import checkpoint
            result = checkpoint(
                message,
                publisher=self.publisher,
                run_id=self.current_run_id,
            )
            return result
        except Exception as e:
            return {"error": str(e)}

    async def git_status(self, log_count: int = 5) -> dict[str, Any]:
        """Get git status and recent commits."""
        denial = self._assert_tool_allowed("git_status")
        if denial:
            return denial
        try:
            from ..git_ops import get_status, log, get_head_sha
            status = get_status()
            commits = log(log_count)
            head = get_head_sha()
            return {
                "head": head[:8] if head else None,
                "status": status,
                "recent_commits": [
                    {"sha": c["sha"][:8], "message": c["message"]}
                    for c in commits
                ]
            }
        except Exception as e:
            return {"error": str(e)}

    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool by name with given arguments."""
        if name == "read_file":
            return await self.read_file(**arguments)
        elif name == "write_file":
            return await self.write_file(**arguments)
        elif name == "edit_file":
            return await self.edit_file(**arguments)
        elif name == "bash":
            return await self.bash(**arguments)
        elif name == "git_checkpoint":
            return await self.git_checkpoint(**arguments)
        elif name == "git_status":
            return await self.git_status(**arguments)
        elif name == "web_search":
            denial = self._assert_tool_allowed("web_search", requires_network=True)
            if denial:
                return denial
            result = await self.web_search.search(**arguments)
            if self.publisher:
                payload = {
                    "query": arguments.get("query"),
                    "max_results": arguments.get("max_results"),
                }
                if self.current_run_id:
                    payload["run_id"] = self.current_run_id
                await self.publisher.publish(
                    "receipt.net",
                    payload,
                    source="agent",
                )
            return result
        elif name == "read_artifact":
            return await self.read_artifact(**arguments)
        elif name == "propose_ahdb":
            return await self.propose_ahdb(**arguments)
        else:
            return {"error": f"Unknown tool: {name}"}
