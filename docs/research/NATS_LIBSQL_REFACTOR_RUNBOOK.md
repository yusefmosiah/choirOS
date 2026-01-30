# NATS + libsql Refactor Runbook (Single Long Codex Session)

**Date**: 2026-01-29  
**Owner**: Codex (this session)  
**Goal**: Refactor ChoirOS to make **NATS JetStream the only source of truth**, and **libsql/Turso the projection store**, with safe concurrency and replayable runs. This runbook is the instruction set to test and implement the refactor in a single long session.

---

## North Star Architecture

**Event Log (SoT)**: NATS JetStream  
**Projection Store**: libsql/Turso (per user database)  
**Runtime**: Machine + tool workers (emit events only)  
**UI**: NATS WS for live, HTTP only for auth/bootstrap + blob fetch  
**Artifacts**: Blob store (local or remote) + `artifact.pointer` events

Principles:
- **No direct writes to projection from runtime.** Runtime emits events only.
- **Single-writer projection** per user (projector service).
- **Replayable**: drop projection, rebuild from NATS.
- **Safe concurrency**: serialization via NATS consumers and tool actors.

---

## Phase 0 — Guardrails & Baseline

### Goals
- Freeze known behavior.
- Capture failing areas (if any).
- Ensure we can rebuild projections from NATS.

### Actions
1. Confirm NATS is up and credentials valid.  
2. Run baseline tests:  
   - `PYTHONPATH=$PWD pytest supervisor/tests/test_runs.py`
3. Capture baseline behavior by running a prompt and verifying artifact creation.

### PREDICTION / EXPERIMENT / OBSERVE (Baseline Test)
```
PREDICTION: A prompt submitted via UI will enqueue a run, execute, and create an artifact.

EXPERIMENT:
1. Start stack (dev.sh)
2. Submit prompt in ? bar
3. Wait for completion

OBSERVE:
- New artifact file in artifacts/
- Run appears in RunMap timeline
```

---

## Phase 1 — Refactor Stores (Projection vs Event Log)

### Goals
- Split storage responsibilities.
- Ensure EventStore never writes projection tables directly (only projector does).

### Actions
1. Introduce `ProjectionStore` interface:
   - Methods: `apply_event`, `commit`, `get_run_timeline`, `list_runs`, etc.
2. Rework current `EventStore` into:
   - `EventPublisher` (NATS only)
   - `ProjectionStore` (libsql)
3. Runtime code must call **publish** only.

### PREDICTION / EXPERIMENT / OBSERVE
```
PREDICTION: Runtime paths emit events to NATS without touching projection tables.

EXPERIMENT:
1. Submit prompt
2. Inspect projection tables: rows only appear via projector, not runtime

OBSERVE:
- No direct writes to libsql from runtime processes
- Projector is sole writer
```

---

## Phase 2 — libsql Projection Store

### Goals
- Replace SQLite projection with libsql.
- Use per-user DBs (e.g., `libsql://choiros-{user}`).
- Track `last_nats_seq` for replay.

### Actions
1. Add libsql client wrapper (sync/async as needed).
2. Implement schema initialization in libsql.
3. Add `projection_state` table:
   - `key TEXT PRIMARY KEY`
   - `value TEXT`
4. Migrate `apply_event` logic to use libsql client.

### PREDICTION / EXPERIMENT / OBSERVE
```
PREDICTION: Projector writes all events into libsql and advances last_nats_seq.

EXPERIMENT:
1. Clear projection DB
2. Replay NATS events via projector
3. Query projection_state.last_nats_seq

OBSERVE:
- last_nats_seq increases
- Run timelines appear in libsql
```

---

## Phase 3 — Projector Worker (Single Writer)

### Goals
- Projector reads NATS and writes projection.
- One projector per user.
- No runtime writes to projection.

### Actions
1. Convert `supervisor/projector_worker.py` into the official projection writer.
2. Use durable consumer with ack + backoff.
3. Store `last_nats_seq` in libsql projection_state.

### PREDICTION / EXPERIMENT / OBSERVE
```
PREDICTION: Projector can stop and resume without data loss or duplication.

EXPERIMENT:
1. Start projector, emit events
2. Stop projector, emit more events
3. Restart projector

OBSERVE:
- Projection catches up to latest NATS seq
- No duplicated rows
```

---

## Phase 4 — Runtime (Machine + Tools)

### Goals
- Machine consumes `run.input` (NATS) and emits `run.started`, `mode.start`, `run.finished`.
- Tool workers consume `tool.call`, emit `tool.result`.
- Filesystem and Git become single-writer tool actors.

### Actions
1. Ensure `Machine` is a NATS consumer only.
2. Remove any polling or SQLite dependency in runtime.
3. Convert auditor to NATS consumer (no SQLite polling).

### PREDICTION / EXPERIMENT / OBSERVE
```
PREDICTION: Multiple concurrent prompts run independently and complete.

EXPERIMENT:
1. Send 10 prompts quickly (multi-window)
2. Observe run status events

OBSERVE:
- All runs finish
- No duplicated run events
- Each run produces one artifact
```

---

## Phase 5 — Replay & Recovery

### Goals
- Full replay of projection from NATS.
- Deterministic rebuilds.

### Actions
1. Add CLI or endpoint: `rebuild_projection(user_id, to_seq=None)`
2. Validate rebuild matches previous projection.

### PREDICTION / EXPERIMENT / OBSERVE
```
PREDICTION: Projection rebuild from NATS reproduces identical run timelines.

EXPERIMENT:
1. Take snapshot of projection counts
2. Wipe projection DB
3. Replay from NATS

OBSERVE:
- Counts match
- Latest run timelines identical
```

---

## Decision Tests (Go/No‑Go for NATS Path)

Run these after Phase 4:

1) **100 concurrent prompts**
```
PREDICTION: All 100 runs complete without duplication or hangs.

EXPERIMENT:
- Emit 100 run.input events quickly

OBSERVE:
- 100 run.finished events
- 100 artifacts
```

2) **Supervisor restart during run**
```
PREDICTION: Runs recover correctly after restart; events replay to projection.

EXPERIMENT:
- Start a run
- Restart supervisor mid-run

OBSERVE:
- Run finishes or safely fails with retry
- Projection consistent
```

3) **Projection rebuild**
```
PREDICTION: Dropping projection and replaying from NATS reconstructs state.

EXPERIMENT:
- Drop libsql projection
- Replay NATS

OBSERVE:
- Timelines match before/after
```

If these tests pass, NATS+libsql stays.  
If they fail, re-evaluate a Ray‑centric execution model (but still keep NATS as log unless a new log is introduced).

---

## Execution Checklist (Single Session)

1. ✅ Confirm baseline tests and current behavior.
2. 🔧 Refactor stores (separate publisher vs projection).
3. 🧱 Implement libsql projection store.
4. 🧵 Wire projector worker (durable consumer).
5. ⚙️ Ensure runtime emits events only.
6. ✅ Run decision tests.
7. 📜 Document results + remaining gaps.

---

## Notes / Constraints

- Use **PREDICTION / EXPERIMENT / OBSERVE** in all new tests.
- Keep comments minimal (complex logic only).
- Don’t add TODOs—either implement or create a follow‑up doc.
- Avoid direct projection writes in runtime code.

