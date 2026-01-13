# ChoirOS Agent Tools

> Minimal, unrestricted, token-efficient.

---

## Design Principles

1. **Minimal surface**: 4 tools total
2. **Task-scoped access**: Director sets `allowed_tools` per task
3. **Token efficient**: Stream large outputs to files
4. **Never lose data**: Logs retained 30 days

---

## The Four Tools

### 1. `read_file`

```python
{
    "name": "read_file",
    "description": "Read file contents. Use head/tail for large files.",
    "input_schema": {
        "path": str,
        "head": int | None,  # First N lines
        "tail": int | None   # Last N lines
    }
}
```

### 2. `write_file`

```python
{
    "name": "write_file",
    "description": "Create or overwrite file with content.",
    "input_schema": {
        "path": str,
        "content": str
    }
}
```

### 3. `edit_file`

```python
{
    "name": "edit_file",
    "description": "Replace exact text matches. Returns diff.",
    "input_schema": {
        "path": str,
        "edits": [{"old_text": str, "new_text": str}],
        "dry_run": bool = False
    }
}
```

**Why text match over line numbers:** Robust to concurrent edits. If file changes between read and edit, line numbers break.

### 4. `bash`

```python
{
    "name": "bash",
    "description": "Execute shell command. Output streamed to file.",
    "input_schema": {
        "command": str,
        "timeout": int = 300  # 5 min default
    }
}
```

**Returns:**
```json
{
    "exit_code": 0,
    "output_file": "/logs/cmd_abc123.txt",
    "output_preview": "first 500 chars...",
    "truncated": true
}
```

**Behavior:**
- Output streams to `/logs/cmd_{id}.txt`
- Agent gets preview (500 chars) + path to full output
- Logs auto-delete after 30 days
- Persistent session: cwd and env vars persist
- Timeout kills command, returns partial output

---

## Implementation

```python
class BashTool:
    def __init__(self):
        self.env = os.environ.copy()
        self.cwd = "/app"

    async def execute(self, command: str, timeout: int = 300) -> dict:
        cmd_id = str(uuid.uuid4())[:8]
        log_path = LOG_DIR / f"cmd_{cmd_id}.txt"

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=self.cwd,
            env=self.env
        )

        # Stream to file
        with open(log_path, "w") as f:
            async for line in proc.stdout:
                f.write(line.decode())

        await proc.wait()

        content = log_path.read_text()
        return {
            "exit_code": proc.returncode,
            "output_file": str(log_path),
            "output_preview": content[:500],
            "truncated": len(content) > 500
        }
```

---

## What's Excluded

| Feature | Why |
|---------|-----|
| MCP protocol | Call via bash later |
| Directory tools | Use `ls`, `mkdir`, `find` via bash |
| File info/move | Use `stat`, `mv` via bash |

---

*Created: 2025-12-17*
