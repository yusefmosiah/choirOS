# Current Architecture (Jan 23, 2026)

This document captures the current, working architecture of ChoirOS as of 2026-01-23, including the runtime data flows, persistence strategy, and immediate/intermediate next steps.

## Executive Summary
- **Frontend (React/Vite)** provides the desktop UI and the command bar, streaming agent responses over a WebSocket.
- **Supervisor (FastAPI)** orchestrates runs, executes tools, and emits events to NATS JetStream.
- **NATS JetStream** is the required event log (source of truth); SQLite is a projection store.
- **API (FastAPI)** provides parsing utilities and a **file-backed artifact store** (saved under `artifacts/` with an `index.json` catalog).
- **Auditor worker** polls SQLite for file changes and appends `auditor.critique` events.

## System Topology

```mermaid
graph LR
    User[User / Browser]
    Frontend[Frontend (choiros, React/Vite)]
    Supervisor[Supervisor (FastAPI)]
    API[API (FastAPI)]
    SQLite[state.sqlite
(projection store)]
    Artifacts[artifacts/
index.json + files]
    NATS[NATS JetStream
(required)]
    Auditor[Auditor Worker]
    Sandbox[Sandbox Runner
(local or Sprites)]

    User -->|HTTP/WS| Frontend
    Frontend -->|WS /agent| Supervisor
    Frontend -->|HTTP /api| API
    Supervisor -->|Publish| NATS
    Supervisor -->|Project| SQLite
    Supervisor -->|Exec| Sandbox
    API -->|Create/read artifacts| Artifacts
    Auditor -->|Polls| SQLite
```

## Core Data Flows

### 1) Command Bar → Agent → Writer

```mermaid
sequenceDiagram
    participant User
    participant FE as Frontend
    participant Sup as Supervisor
    participant Agent as AgentHarness
    participant NATS as NATS JetStream
    participant DB as SQLite Projection
    participant API as API /artifacts
    participant FS as artifacts/ + index.json

    User->>FE: Enter prompt in command bar
    FE->>Sup: WS /agent {prompt}
    Sup->>NATS: run.input event
    Sup->>Agent: process(prompt)
    Agent-->>FE: streaming thinking/text/tool events
    Sup->>NATS: mode.start event (execution begins)
    Agent->>NATS: tool/file/receipt events
    NATS->>DB: project events
    FE->>API: POST /api/artifacts
    API->>FS: write file + update index.json
    FE->>FE: open Writer with artifactId
```

**Notes:**
- The frontend saves the full prompt/response to an artifact and opens Writer on completion.
- Writer loads the artifact content by ID from the API.

### 2) File Change → Auditor

```mermaid
sequenceDiagram
    participant Agent as Agent Tools
    participant NATS as NATS JetStream
    participant DB as SQLite Projection
    participant Aud as Auditor Worker
    participant Sup as Supervisor

    Agent->>NATS: file.write event
    NATS->>DB: project events
    Aud->>DB: poll new events
    Aud->>Sup: run audit on changed file
    Aud->>DB: append auditor.critique event
```

**Notes:**
- The auditor is a background loop polling SQLite. It is not NATS-driven today.

### 3) Mode Directives via NATS (Required)

```mermaid
sequenceDiagram
    participant NATS
    participant Sup as Supervisor Machine
    participant Agent as AgentHarness

    NATS->>Sup: mode.directive event
    Sup->>Agent: execute mode run
    Agent-->>Sup: streaming output
```

**Notes:**
- The supervisor listens for directives and executes them through the Machine + RunOrchestrator.

## Storage Model (Current)

### Event Log
- **Source of truth:** NATS JetStream
- **Event structure:** event type + JSON payload, with `nats_seq` assigned by NATS
- **SQLite:** projection store that mirrors NATS for queries and UI

### Artifacts
- **Physical storage:** `artifacts/` directory
- **Index:** `artifacts/index.json`
- **API usage:** `POST /api/artifacts` writes file + index; `GET /api/artifacts/{id}` returns content.

### Workspace Files
- The repo itself is the working filesystem. Tool writes generate `file.write` events and are audited by the worker loop.

## Runtime Components

### Frontend (`/choiros`)
- Web desktop UI with command bar.
- Opens Writer windows for artifact content.

### Supervisor (`/supervisor`)
- Orchestrates runs and executes tools.
- Emits events into SQLite and optionally NATS.
- Hosts `/agent` WebSocket for streaming agent responses.

### API (`/api`)
- Parsing endpoints for URLs/uploads.
- Artifact CRUD endpoints backed by the filesystem.

### Auditor Worker (`/supervisor/auditor_worker.py`)
- Polls SQLite for file changes and records critiques.

### NATS JetStream (optional)
- Event bus + directive channel.
- Used for publish/subscribe when enabled.

## Known Bottlenecks and Risks
- **Event throughput:** UI event stream can be noisy; no batching or backpressure.
- **Dual persistence:** SQLite is authoritative in local dev; NATS only partially used, which complicates recovery semantics.
- **Artifact index drift:** legacy in-memory artifacts can leave name/path inconsistencies in `index.json`.

## Immediate Next Steps (1–2 weeks)
1. **Decide source-of-truth** (NATS-only vs SQLite-first) and implement a projector if moving to NATS-only.
2. **Artifact migration**: normalize legacy artifact names/paths and add a simple backfill command.
3. **Stream hygiene**: add batching/backpressure for event stream and reduce redundant toasts.

## Intermediate Next Steps (1–2 months)
1. **JetStream projector → libsql**: move projections to libsql (or Turso) with replay capability.
2. **Work-queue execution**: decouple command bar from run execution; queue work and visualize state.
3. **Visualization graph**: map receipts, artifacts, AHDB deltas, and verifier outcomes.
4. **AgentFS integration**: standardize filesystem diffs as canonical state changes.

## Related Docs
- `docs/ARCHITECTURE_OVERVIEW.md`
- `docs/specs/CHOIR_EVENT_CONTRACT_SPEC.md`
- `docs/specs/CHOIR_MACHINE_V0_SPEC.md`
- `docs/specs/CHOIR_AGENTFS_INTEGRATION_SPEC.md`
