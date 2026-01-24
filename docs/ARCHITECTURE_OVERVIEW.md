# ChoirOS Architecture Overview
Updated: 2026-01-23

This document provides a high-level overview of the ChoirOS architecture, capturing the relationships between the Supervisor, API, ChoirOS Frontend, NATS, sandboxes, and the worker loop.

## System Diagram

```mermaid
graph TD
    User[User / Browser] -->|HTTP/WS| Frontend[ChoirOS Frontend (Vite)]
    User -->|HTTP/WS| Supervisor[Supervisor (Brain)]
    Frontend -->|HTTP| API[API Service]
    Frontend -->|WS| Supervisor
    Supervisor -->|JetStream (optional)| NATS[NATS Message Bus]
    Supervisor -->|HTTP/WS| Sprites[Sprites.dev (Remote Sandbox)]
    Supervisor -->|Subprocess| LocalAPI[API Service (Docker Mode)]
    Supervisor -->|Subprocess| LocalVite[Vite Dev Server (Docker Mode)]
    API -->|File-backed artifacts| Artifacts[artifacts/ + index.json]
    Supervisor -->|SQLite event log| SQLite[state.sqlite]
    Auditor[Auditor Worker] -->|Polls| SQLite
```

## Core Components

### 1. Supervisor (`/supervisor`)
**The Brain & Orchestrator.**
- **Role**: The central nervous system of ChoirOS. It manages the agent lifecycle, state, and external integrations.
- **Tech**: FastAPI (Python).
- **Key Responsibilities**:
    - **Agent Orchestration**: managed via `AgentHarness` and `RunOrchestrator`.
    - **Event Sourcing**: Connects to NATS JetStream to store and replay events (if enabled).
    - **File History**: Manages undo/redo functionality for file operations.
    - **Sandbox Management**: Provisions and executes code in sandboxes (Local or Sprites).
    - **WebSocket Gate**: Provides the real-time interface (`/agent`) for the frontend "Chat" or "?" command bar.
- **Entry Point**: `supervisor.main:app` running on port `8001`.

### 2. API Service (`/api`)
**Utilities & Helpers.**
- **Role**: A lightweight service for stateless or specific utility operations.
- **Tech**: FastAPI (Python).
- **Key Responsibilities**:
    - **Parsing**: `api.routers.parse` for URL/content extraction.
    - **Artifacts**: `api.routers.artifacts` for file-backed artifact storage (saved in `artifacts/`).
    - **Auth**: `api.routers.auth` for session validation.
- **Entry Point**: `api.main:app` running on port `8000`.

### 3. ChoirOS Frontend (`/choiros`)
**The Desktop Interface.**
- **Role**: The user-facing "Web Desktop".
- **Tech**: React, Vite, TypeScript.
- **Communication**:
    - Talks to **Supervisor** via WebSockets for the Agent/Chat interface.
    - Talks to **API** for specific data needs.
- **Entry Point**: `npm run dev` running on port `5173`.

### 4. NATS (`docker-compose.yml`)
**The Nervous System.**
- **Role**: Distributed messaging and event store.
- **Tech**: NATS JetStream (Docker image `nats:2.10-alpine`).
- **Usage**: Used by Supervisor to store the "Stream of Consciousness" (events) and mode directives when enabled. SQLite still holds the local event log and projections.

### 5. Auditor Worker (`/supervisor/auditor_worker.py`)
**Background Audit Loop.**
- **Role**: Watches file changes and writes critiques to the event log.
- **Mechanism**: Polls the SQLite event log for `file.write` events and records `auditor.critique`.

### 6. Sprites (`supervisor/sprites_adapter.py`)
**Remote Execution Environment.**
- **Role**: A secure, remote sandbox for running code.
- **Integration**: The Supervisor uses the `SpritesSandboxRunner` to:
    - Create ephemeral environments (`POST /v1/sprites`).
    - Execute commands (`POST /v1/sprites/.../exec`).
    - Manage file checkpoints.
- **Provider Switching**: Controlled by `CHOIR_SANDBOX_PROVIDER` env var. Defaults to `local` (subprocess) if Sprites is not configured.

## Development Workflow (`dev.sh`)

The `dev.sh` script is the "Control Center" for local development.

1.  **Checks Environment**: Sets up Python venv, installs requirements.
2.  **Starts NATS**: Uses Docker Compose to spin up the NATS container.
3.  **Starts Supervisor**: Runs `supervisor.main` on port 8001.
4.  **Starts API**: Runs `api.main` (uvicorn) on port 8000.
5.  **Starts Auditor**: Runs `supervisor/auditor_worker.py`.
6.  **Starts Frontend**: Runs `npm run dev` in `choiros/` on port 5173.

All services run in parallel. In Docker-based deployment, the Supervisor acts as the parent process that spawns the others, but in local dev (`SUPERVISOR_STANDALONE=1`), they run independently.

See `docs/MASTER_DOC.md` for the canonical architecture spine and
`docs/archive/snapshots/current_architecture_jan23.md` for the historical snapshot.
