"""
ChoirOS Supervisor - Main entry point.

Manages:
- File history for undo
- Agent WebSocket endpoint
- NATS JetStream connection for event sourcing
- (In Docker only) Vite dev server subprocess
- (In Docker only) FastAPI backend subprocess
"""

import asyncio
import os
import signal
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .vite_manager import ViteManager
from .file_history import FileHistory
from .agent.harness import AgentHarness
from .nats_client import get_nats_client, close_nats_client
from .db import get_store


def _get_project_root() -> Path:
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        return Path(pythonpath.split(":")[0])
    return Path(__file__).parent.parent


PROJECT_ROOT = _get_project_root()

# Load environment variables from api/.env
env_file = PROJECT_ROOT / "api" / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Check if running standalone (local dev) vs Docker (manages subprocesses)
STANDALONE = os.environ.get("SUPERVISOR_STANDALONE", "0") == "1"

# NATS enabled flag
NATS_ENABLED = os.environ.get("NATS_ENABLED", "1") == "1"

# Global instances
vite_manager = ViteManager()
file_history = FileHistory()
agent_harness: AgentHarness | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    global agent_harness

    # Initialize NATS connection (if enabled)
    nats_connected = False
    if NATS_ENABLED:
        try:
            nats = await get_nats_client()
            nats_connected = True
            print("✓ NATS JetStream connected")
        except Exception as e:
            print(f"⚠ NATS connection failed (running without event sourcing): {e}")

    # Initialize event store (will use NATS if connected)
    store = get_store()

    # Initialize agent harness
    agent_harness = AgentHarness(file_history=file_history)

    api_process = None

    if not STANDALONE:
        # Docker mode: start Vite and API as subprocesses
        await vite_manager.start()

        api_process = await asyncio.create_subprocess_exec(
            "uvicorn", "api.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            cwd=str(PROJECT_ROOT)
        )

    yield

    # Shutdown
    if not STANDALONE:
        await vite_manager.stop()
        if api_process:
            api_process.terminate()
            await api_process.wait()

    # Close NATS connection
    if nats_connected:
        await close_nats_client()
        print("✓ NATS connection closed")


app = FastAPI(
    title="ChoirOS Supervisor",
    description="Manages file history, agent communication, and NATS event sourcing",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS for browser connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    store = get_store()
    nats_status = "disabled"

    if NATS_ENABLED:
        try:
            nats = await get_nats_client()
            nats_status = "connected"
        except:
            nats_status = "disconnected"

    return {
        "status": "ok",
        "standalone": STANDALONE,
        "nats": nats_status,
        "vite_running": vite_manager.is_running() if not STANDALONE else "n/a",
        "file_history_size": file_history.size(),
        "event_seq": store.get_latest_seq(),
    }


@app.post("/undo")
async def undo(count: int = 1):
    """Undo the last N file changes."""
    restored = await file_history.undo(count)

    # Restart Vite if files were restored (Docker mode only)
    if restored and not STANDALONE:
        await vite_manager.restart()

    return {
        "restored_files": restored,
        "count": len(restored),
    }


# =========== Git Endpoints ===========

@app.get("/git/status")
async def git_status():
    """Get git status and HEAD info."""
    from .git_ops import get_status, get_head_sha

    status = get_status()
    head = get_head_sha()

    return {
        "head": head[:8] if head else None,
        "head_full": head,
        "status": status,
    }


@app.get("/git/log")
async def git_log(count: int = 10):
    """Get recent commits."""
    from .git_ops import log

    commits = log(count)
    return {
        "commits": commits,
        "count": len(commits),
    }


@app.post("/git/checkpoint")
async def git_checkpoint(message: Optional[str] = None):
    """Create a git checkpoint (add all + commit)."""
    from .git_ops import checkpoint

    result = checkpoint(message)
    return result


@app.post("/git/revert")
async def git_revert(sha: str, dry_run: bool = True):
    """Safely revert to a specific commit with backup."""
    from .git_ops import git_revert

    result = git_revert(sha, dry_run=dry_run)

    if result.get("success") and not dry_run and not STANDALONE:
        await vite_manager.restart()

    return result


@app.websocket("/agent")
async def agent_websocket(websocket: WebSocket):
    """WebSocket endpoint for agent communication."""
    await websocket.accept()

    try:
        while True:
            # Receive prompt from ? bar
            data = await websocket.receive_json()
            prompt = data.get("prompt", "")

            if not prompt:
                await websocket.send_json({"type": "error", "content": "No prompt provided"})
                continue

            # Process with agent
            if agent_harness is None:
                await websocket.send_json({"type": "error", "content": "Agent harness not ready"})
                continue

            async for response in agent_harness.process(prompt):
                await websocket.send_json(response)

    except WebSocketDisconnect:
        pass


def main():
    """Run the supervisor server."""
    import uvicorn

    # Handle SIGTERM gracefully
    def handle_sigterm(signum, frame):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)

    # Determine reload directories
    reload_dirs = [str(PROJECT_ROOT / "supervisor")]

    uvicorn.run(
        "supervisor.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        reload_dirs=reload_dirs,
    )


if __name__ == "__main__":
    main()
