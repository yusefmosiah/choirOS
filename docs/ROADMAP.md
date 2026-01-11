# ChoirOS Implementation Roadmap

## Current State (Jan 2026)

### What Works ✅
- Web desktop shell (window manager, taskbar, apps)
- FastAPI parsing backend + artifact pipeline
- Supervisor runtime + agent harness (Bedrock)
- Git checkpoint API + GitPanel UI
- Local dev orchestration via `dev.sh`

### In Progress 🔄
- Event stream UI (needs live NATS wiring)
- NATS client (browser + supervisor, untested)
- Git-based self-hosted deployment loop

### Not Started 📐
- Firecracker microVM orchestration
- S3/SQLite sync for per-user state
- Citation graph + economic layer

---

## Phase 3: Agent Platform (Now)

**Goal:** An automatic computer that can modify itself safely, with visible actions and reversible state.

**Foundational Layer**
1. **User/Auth abstraction**
   - Issue identity + token
   - `user_id` required on every event
2. **NATS namespacing**
   - Per-user subjects + durable consumers

**Source of Truth**
3. **Event-first logging**
   - Write/edit/delete emits event immediately
   - SQLite + filesystem updated by projector
4. **Undo as event**
   - `UNDO(target_seq)` published by supervisor
   - Projector rebuilds via replay + snapshots

**Deployment Loop**
5. **In-app deploy pipeline**
   - `DEPLOY_REQUEST` → CI/CD → `DEPLOY_RESULT`
   - UI displays deploy status from events

**Product hygiene**
6. **Event stream wiring**
   - NATS connection + event sink
   - EventStream UI consuming real events
7. **Stub cleanup**
   - Remove demo-only UI or mark as explicitly “mock”

---

## Phase 4: Persistence

**Goal:** State survives sessions.

**Deliverables:**
- Per-user SQLite in sandbox
- S3 sync for artifacts + DB
- Workspace export/import

---

## Phase 5: Publishing

**Goal:** Artifacts become shareable and attributable.

**Deliverables:**
- Public artifact URLs
- Citation metadata and queries
- Export with provenance

---

## Phase 6+: Collective Intelligence

**Goal:** Cross-user discovery and rewards.

**Deliverables:**
- Global NATS mesh
- Citation rewards + governance
- Custom domains as identity

---

## Ordered Checklist (Next Actions)

1. Define `user_id` + auth token shape for supervisor and UI
2. Update NATS subjects to `choiros.{user_id}.{source}.{type}`
3. Emit NATS events from agent tool writes/edits/deletes
4. Build projector service to materialize SQLite + filesystem
5. Implement `UNDO` event + replay endpoint
6. Add snapshotting for fast replay
7. Wire EventStream UI to live NATS events
8. Add deploy events (`DEPLOY_REQUEST`/`DEPLOY_RESULT`)
