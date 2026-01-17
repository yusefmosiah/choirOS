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

from ..db import EventStore, get_store


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
    """Implementation of the 4 agent tools."""

    def __init__(self, file_history=None, event_store: Optional[EventStore] = None):
        """
        Initialize tools.

        Args:
            file_history: Optional FileHistory instance for undo support
            event_store: Optional EventStore for logging file mutations
        """
        self.file_history = file_history
        self.store = event_store or get_store()
        self.env = os.environ.copy()
        self.cwd = str(PROJECT_ROOT / "choiros")  # Default working directory
        self.app_dir = PROJECT_ROOT

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
        }
    ]

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to app_dir if not absolute."""
        p = Path(path)
        if not p.is_absolute():
            p = self.app_dir / path
        return p

    def _display_path(self, path: Path) -> str:
        """Prefer app-relative paths for event payloads."""
        try:
            return str(path.relative_to(self.app_dir))
        except ValueError:
            return str(path)

    async def read_file(self, path: str, head: int | None = None, tail: int | None = None) -> dict[str, Any]:
        """Read file contents."""
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

            return {
                "content": "\n".join(lines),
                "total_lines": len(content.splitlines()),
                "returned_lines": len(lines),
            }

        except Exception as e:
            return {"error": str(e)}

    async def write_file(self, path: str, content: str) -> dict[str, Any]:
        """Write content to a file."""
        try:
            file_path = self._resolve_path(path)

            # Save state for undo before writing
            if self.file_history:
                await self.file_history.save_state(str(file_path))

            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            file_path.write_text(content)

            if self.store:
                await self.store.log_file_write_async(self._display_path(file_path), content.encode())

            return {
                "success": True,
                "path": str(file_path),
                "bytes_written": len(content.encode()),
            }

        except Exception as e:
            return {"error": str(e)}

    async def edit_file(
        self,
        path: str,
        edits: list[dict[str, str]],
        dry_run: bool = False
    ) -> dict[str, Any]:
        """Apply text replacements to a file."""
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
                if self.store:
                    await self.store.log_file_write_async(self._display_path(file_path), content.encode())

            return {
                "success": True,
                "path": str(file_path),
                "changes": changes,
                "modified": content != original,
            }

        except Exception as e:
            return {"error": str(e)}

    async def bash(self, command: str, timeout: int = 300) -> dict[str, Any]:
        """Execute a shell command."""
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

            return {
                "exit_code": proc.returncode,
                "output_file": str(log_path),
                "output_preview": preview,
                "truncated": len(content) > 500,
            }

        except Exception as e:
            return {"error": str(e)}

    async def git_checkpoint(self, message: Optional[str] = None) -> dict[str, Any]:
        """Create a git checkpoint."""
        try:
            from ..git_ops import checkpoint
            result = checkpoint(message)
            return result
        except Exception as e:
            return {"error": str(e)}

    async def git_status(self, log_count: int = 5) -> dict[str, Any]:
        """Get git status and recent commits."""
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
        else:
            return {"error": f"Unknown tool: {name}"}
