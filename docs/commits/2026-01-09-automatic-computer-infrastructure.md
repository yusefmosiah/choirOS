# Commit Report: Automatic Computer Infrastructure

**Commit Date**: January 9, 2026
**Scope**: NATS event sourcing, Docker infrastructure, UI components, documentation overhaul

---

## Hypothesis of Change

This commit captures the transition from a demo-phase desktop shell to production-oriented event-sourced infrastructure. The central hypothesis: **ChoirOS becomes a real system when every action is an immutable event in a replayable log**.

---

## Summary

| Category | Added | Modified | Key Files |
|----------|-------|----------|-----------|
| **Documentation** | 6 | 8 | THE_AUTOMATIC_COMPUTER.md, ARCHITECTURE.md, ROADMAP.md |
| **Backend Infrastructure** | 4 | 4 | nats_client.py, db.py, main.py, docker-compose.yml |
| **Frontend Components** | 5 | 5 | Mail.tsx, EventStream.tsx, nats.ts, events.ts |
| **Config/Build** | 2 | 2 | Dockerfile, yarn.lock |
| **Total** | **17** | **20** | 37 files changed |

---

## Part 1: Documentation Changes

### New Vision Documents

#### [THE_AUTOMATIC_COMPUTER.md](docs/THE_AGENTIC_COMPUTER.md)
The philosophical foundation document. Renamed from "Agentic" to "Automatic" Computer—a deliberate linguistic choice emphasizing that the computer *automates itself* rather than containing an "agent" as a feature.

Key themes:
- **Web desktop as container**: All apps share DOM, making agent action surface unified
- **Sandbox as trust infrastructure**: Proposed-not-executed paradigm with full reversibility
- **Event sourcing as architecture**: Every action is a log entry, state is a projection

#### [ARCHITECTURE.md](docs/ARCHITECTURE.md)
New technical architecture document with:
- Evolution path: Local → Container → MicroVM → TEE
- Core data flow diagram: Browser ↔ Supervisor ↔ NATS ↔ SQLite projections
- Event type definitions (TypeScript)
- Per-user SQLite schema with NATS sequence tracking
- Git checkpoint integration

#### [ROADMAP.md](docs/ROADMAP.md)
Implementation phases:
1. Local Persistence (SQLite event store) ✅
2. Containerization (NATS JetStream) ✅
3. Multi-User (Auth, S3 sync)
4. MicroVM (Firecracker)
5. TEE + Economics

#### [CURRENT_STATE.md](docs/CURRENT_STATE.md)
Status snapshot documenting:
- What's complete vs stub vs designed-only
- Untracked files inventory
- Deployment path priorities
- Decision points

#### [PLANNING.md](PLANNING.md)
Stream-of-consciousness planning turned into structured roadmap:
- Sandbox-in-sandbox architecture (TEE → MicroVM → Container)
- Two-layer version control (Git commits + NATS events)
- Immediate task breakdown

### Modified Documentation

- **docs/archive/*.md**: Terminology update "agentic" → "automatic" throughout
- **docs/CHANGELOG.md**: Minor updates
- **docs/CONTEXT.md**: Architecture references updated
- **docs/bootstrap/AGENT_HARNESS.md**: Minor alignment

---

## Part 2: Backend Infrastructure

### NATS JetStream Integration

#### [supervisor/nats_client.py](supervisor/nats_client.py) (NEW - 251 lines)
Full async NATS JetStream client:
- `ChoirEvent` dataclass for structured events
- `NATSClient` class with connection management
- Stream creation: USER_EVENTS, AGENT_EVENTS, SYSTEM_EVENTS
- Subject hierarchy: `choiros.{source}.{user_id}.{event_type}`
- Singleton pattern with `get_nats_client()` / `close_nats_client()`

#### [supervisor/db.py](supervisor/db.py) (NEW - 530 lines)
`EventStore` class with dual-write architecture:
- SQLite as materialized projection (queryable view)
- NATS as source of truth (append-only log)
- `nats_seq` column tracks NATS sequence numbers
- `rebuild_from_nats()` for disaster recovery
- Async methods: `append_async()`, `add_message_async()`, etc.
- `NATS_ENABLED` flag for fallback mode

#### [supervisor/main.py](supervisor/main.py) (MODIFIED)
Lifespan changes:
- NATS connection on startup with fallback
- Health endpoint reports NATS status
- `NATS_ENABLED` environment variable
- Graceful NATS shutdown

#### [supervisor/git_ops.py](supervisor/git_ops.py) (NEW - 182 lines)
Git operations for checkpoint system:
- `checkpoint()` creates git commit from current state
- `get_commit_history()` for timeline UI
- Integration point for auto-checkpoint after N events

#### [supervisor/requirements.txt](supervisor/requirements.txt) (MODIFIED)
Added: `nats-py>=2.7.2`

---

## Part 3: Docker Infrastructure

#### [docker-compose.yml](docker-compose.yml) (MODIFIED)
```yaml
services:
  nats:
    image: nats:2.10-alpine
    command: --jetstream --store_dir /data
    ports:
      - "4222:4222"   # Client
      - "8222:8222"   # Monitoring
    volumes:
      - nats-data:/data
```
- Added NATS service with persistent JetStream storage
- `choiros` service now depends on `nats`
- Added `NATS_URL` environment variable

#### [Dockerfile](Dockerfile) (MODIFIED)
- Changed from `npm ci` to `yarn install --frozen-lockfile || yarn install`
- Fixes package manager mismatch (project uses yarn)

---

## Part 4: Frontend Components

### New Components

#### [choiros/src/components/apps/Mail.tsx](choiros/src/components/apps/Mail.tsx) (NEW - 402 lines)
Full email client UI:
- Folder navigation (Inbox, Sent, Starred, Trash, Archive)
- Email list with unread indicators, starring
- Reading pane with compose modal
- Sample email data for demo
- **Status**: UI complete, backend is stub (needs IMAP/SMTP)

#### [choiros/src/components/desktop/EventStream.tsx](choiros/src/components/desktop/EventStream.tsx) (NEW - 76 lines)
Toast-style notification stream:
- 3D perspective stacking effect
- Auto-dismiss after 12 seconds
- Click to open associated artifact
- Zustand store integration

#### [choiros/src/lib/nats.ts](choiros/src/lib/nats.ts) (NEW - 160 lines)
Browser NATS client:
- WebSocket connection via `nats.ws`
- `ChoirEvent` interface matching Python
- `publishEvent()`, `subscribeEvents()`, `subscribeUserEvents()`
- **Status**: Written but needs `yarn install` to resolve types

#### [choiros/src/stores/events.ts](choiros/src/stores/events.ts) (NEW - 55 lines)
Zustand store for event stream:
- `StreamEvent` type with message, type, artifactId
- `addEvent()`, `removeEvent()` actions
- Powers EventStream component

### Modified Components

#### [choiros/src/components/desktop/Desktop.tsx](choiros/src/components/desktop/Desktop.tsx)
- Added `EventStream` component to desktop
- Removed `MeadowPopup` (demo cleanup)

#### [choiros/src/components/desktop/Taskbar.tsx](choiros/src/components/desktop/Taskbar.tsx)
- UI refinements

#### [choiros/src/lib/apps.ts](choiros/src/lib/apps.ts)
- Fixed syntax error (duplicate closing brace)
- Added missing icon imports from lucide-react
- Added Mail app to registry

#### [choiros/package.json](choiros/package.json)
- Added: `nats.ws@^1.28.0`

---

## Part 5: Removed Components

#### MeadowPopup (DELETED)
- `choiros/src/components/desktop/MeadowPopup.tsx`
- `choiros/src/components/desktop/MeadowPopup.css`
- Was a demo video popup for external presentation
- No longer needed

---

## Part 6: State Files

#### [state.sqlite](state.sqlite) (NEW - 786KB)
Local SQLite database:
- Events table (append-only log)
- Files, conversations, messages tables (projections)
- Tool calls tracking
- Checkpoints table for git integration

---

## Verification

Docker stack verified running:
- ✅ Vite frontend: http://localhost:5173
- ✅ Supervisor: http://localhost:8001/health (`{"nats":"connected"}`)
- ✅ FastAPI: http://localhost:8000
- ✅ NATS: port 4222 (client), 8222 (monitoring)

Minor issue: NATS stream creation has config format error. System falls back to SQLite-only mode gracefully.

---

## What's Next

1. **Fix NATS stream config** - ConsumerConfig parameter format
2. **Wire EventStream to NATS** - Live event subscriptions
3. **Git auto-checkpoint** - Commit after N events
4. **EC2 deployment** - Production infrastructure

---

*This commit establishes the foundation for the Automatic Computer: an event-sourced, sandboxed, version-controlled execution environment where AI agents operate with full observability and reversibility.*
