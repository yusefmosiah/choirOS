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
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from .vite_manager import ViteManager
from .file_history import FileHistory
from .agent.harness import AgentHarness
from .nats_client import get_nats_client, close_nats_client
from .db import get_store
from .run_orchestrator import RunOrchestrator


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

# WebSocket limits (defensive defaults)
MAX_PROMPT_CHARS = int(os.environ.get("WS_MAX_PROMPT_CHARS", "20000"))
WS_RATE_WINDOW_SECONDS = int(os.environ.get("WS_RATE_WINDOW_SECONDS", "10"))
WS_MAX_PROMPTS_PER_WINDOW = int(os.environ.get("WS_MAX_PROMPTS_PER_WINDOW", "5"))

# Global instances
vite_manager = ViteManager()
file_history = FileHistory()


class WorkItemPayload(BaseModel):
    id: Optional[str] = None
    description: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    required_verifiers: Optional[list[str]] = None
    risk_tier: Optional[str] = None
    dependencies: Optional[list[str]] = None
    status: Optional[str] = None
    parent_id: Optional[str] = None


class RunCreatePayload(BaseModel):
    work_item_id: str
    mood: Optional[str] = None
    status: Optional[str] = "created"


class RunUpdatePayload(BaseModel):
    status: Optional[str] = None
    mood: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class RunNotePayload(BaseModel):
    note_type: str = Field(..., description="Canonical note event type")
    body: dict


class RunVerificationPayload(BaseModel):
    attestation: dict


class RunCommitRequestPayload(BaseModel):
    payload: dict


def _get_cors_settings() -> tuple[list[str], bool]:
    raw = os.environ.get("CORS_ALLOW_ORIGINS")
    if raw:
        origins = [item.strip() for item in raw.split(",") if item.strip()]
    else:
        origins = ["http://localhost:5173"]
    if "*" in origins:
        return ["*"], False
    return origins, True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""

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
cors_origins, cors_allow_credentials = _get_cors_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_allow_credentials,
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


# =========== Run / Work Item Endpoints ===========

@app.post("/work_item")
async def work_item_upsert(payload: WorkItemPayload):
    store = get_store()
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    work_item_id = data.pop("id", None)

    if work_item_id:
        existing = store.get_work_item(work_item_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Work item not found")
        updated = store.update_work_item(work_item_id, data)
        return {"work_item": updated}

    if not payload.description:
        raise HTTPException(status_code=400, detail="description is required to create work item")

    created = store.create_work_item(
        description=payload.description,
        acceptance_criteria=payload.acceptance_criteria,
        required_verifiers=payload.required_verifiers,
        risk_tier=payload.risk_tier,
        dependencies=payload.dependencies,
        status=payload.status or "pending",
        parent_id=payload.parent_id,
    )
    return {"work_item": created}


@app.get("/work_item/{work_item_id}")
async def get_work_item(work_item_id: str):
    store = get_store()
    item = store.get_work_item(work_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Work item not found")
    return {"work_item": item}


@app.get("/work_items")
async def list_work_items(status: Optional[str] = None, limit: int = 50):
    store = get_store()
    return {"work_items": store.list_work_items(status=status, limit=limit)}


@app.post("/run")
async def create_run(payload: RunCreatePayload):
    store = get_store()
    work_item = store.get_work_item(payload.work_item_id)
    if not work_item:
        raise HTTPException(status_code=404, detail="Work item not found")
    run = store.create_run(
        work_item_id=payload.work_item_id,
        mood=payload.mood,
        status=payload.status or "created",
    )
    return {"run": run}


@app.patch("/run/{run_id}")
async def update_run(run_id: str, payload: RunUpdatePayload):
    store = get_store()
    existing = store.get_run(run_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Run not found")
    updated = store.update_run(run_id, payload.model_dump(exclude_unset=True, exclude_none=True))
    return {"run": updated}


@app.get("/run/{run_id}")
async def get_run(run_id: str):
    store = get_store()
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"run": run}


@app.get("/runs")
async def list_runs(status: Optional[str] = None, limit: int = 50):
    store = get_store()
    return {"runs": store.list_runs(status=status, limit=limit)}


@app.post("/run/{run_id}/note")
async def add_run_note(run_id: str, payload: RunNotePayload):
    store = get_store()
    if not store.get_run(run_id):
        raise HTTPException(status_code=404, detail="Run not found")
    event_seq = store.add_run_note(run_id, payload.note_type, payload.body)
    return {"event_seq": event_seq}


@app.post("/run/{run_id}/verify")
async def add_run_verification(run_id: str, payload: RunVerificationPayload):
    store = get_store()
    if not store.get_run(run_id):
        raise HTTPException(status_code=404, detail="Run not found")
    event_seq = store.add_run_verification(run_id, payload.attestation)
    return {"event_seq": event_seq}


@app.post("/run/{run_id}/commit_request")
async def add_commit_request(run_id: str, payload: RunCommitRequestPayload):
    store = get_store()
    if not store.get_run(run_id):
        raise HTTPException(status_code=404, detail="Run not found")
    event_seq = store.add_commit_request(run_id, payload.payload)
    return {"event_seq": event_seq}


@app.get("/state/ahdb")
async def get_ahdb_state():
    store = get_store()
    return {"ahdb": store.get_ahdb_state()}


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
    store = get_store()
    agent_harness = AgentHarness(file_history=file_history, event_store=store)
    orchestrator = RunOrchestrator(store=store)
    recent_prompts = deque()
    verifier_config = PROJECT_ROOT / "config" / "verifiers.yaml"

    try:
        while True:
            # Receive prompt from ? bar
            data = await websocket.receive_json()
            prompt = data.get("prompt", "")

            if not prompt:
                await websocket.send_json({"type": "error", "content": "No prompt provided"})
                continue

            if len(prompt) > MAX_PROMPT_CHARS:
                await websocket.send_json({
                    "type": "error",
                    "content": f"Prompt too large (max {MAX_PROMPT_CHARS} chars)"
                })
                continue

            now = time.monotonic()
            while recent_prompts and now - recent_prompts[0] > WS_RATE_WINDOW_SECONDS:
                recent_prompts.popleft()
            if len(recent_prompts) >= WS_MAX_PROMPTS_PER_WINDOW:
                await websocket.send_json({
                    "type": "error",
                    "content": "Rate limit exceeded, please slow down."
                })
                continue
            recent_prompts.append(now)

            # Create a work item per prompt
            work_item = store.create_work_item(description=prompt, status="queued")

            async def execute_run(_: dict) -> bool:
                success = True
                async for response in agent_harness.process(prompt):
                    if response.get("type") == "error":
                        success = False
                    await websocket.send_json(response)
                return success

            result = await orchestrator.run_async(
                work_item_id=work_item["id"],
                execute_run=execute_run,
                mood="CALM",
                config_path=verifier_config,
            )

            run = result.get("run") or {}
            status = run.get("status")
            if status == "verified":
                store.update_work_item(work_item["id"], {"status": "done"})
            elif status == "failed":
                store.update_work_item(work_item["id"], {"status": "failed"})

            await websocket.send_json({
                "type": "verification",
                "content": {
                    "run": run,
                    "verifier_plan": result.get("verifier_plan"),
                    "results": [
                        {"id": r.verifier_id, "status": r.status}
                        for r in result.get("verifier_results", [])
                    ],
                }
            })

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
