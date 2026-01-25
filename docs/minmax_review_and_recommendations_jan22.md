# ChoirOS Review and Recommendations

**Date:** January 22, 2026
**Author:** Code Review (OpenCode)

---

## Executive Summary

ChoirOS is a sophisticated concept with significant architectural debt. The core ideas are sound—AHDB state vector, modes as deterministic agent configurations, zettelkasten knowledge substrate—but the implementation is fragmented across premature infrastructure and unclear boundaries. Code velocity has slowed because the mental model doesn't match the code.

This document identifies the key issues and provides a staged plan to simplify, clarify, and enable the bootstrapping goal (building Choir within Choir).

---

## 1. Current State Assessment

### 1.1 What Exists

| Component | Status | Notes |
|-----------|--------|-------|
| **Supervisor** | Functional but monolithic | 600+ line main.py, 10+ responsibilities |
| **API Service** | Functional | Parse, artifacts, auth routers |
| **Frontend (ChoirOS)** | Functional | React desktop UI, window manager, Writer app |
| **EventStore (AHDB)** | Partially functional | SQLite with runs, notes, receipts, ahdb_state tables |
| **Modes (Modes)** | Implemented | mode_engine.py, verifier_plan.py, but called "modes" not "modes" |
| **Unilateral Auditor** | Partial | auditor.baml, auditor.py, auditor_worker.py exists but not integrated |
| **Verifier System** | Functional | 10 verifiers in verifiers.yaml, verifier_runner.py |
| **FileHistory** | In-memory only | Lost on restart |
| **ArtifactStore** | In-memory only | Lost on restart |
| **NATS** | Enabled by default | Likely premature for single-user use case |

### 1.2 What Doesn't Match

| Concept (Docs) | Implementation | Gap |
|----------------|----------------|-----|
| Zettelkasten substrate | No content-addressing, no edges | Major gap |
| DOCTRINE / SPEC / NOTES tiers | Docs exist but not enforced | Partial gap |
| BACKLINKS ARE PROJECTIONS | Manual backlink lists in docs | Violates doctrine |
| AHDB IS STATE VECTOR | Implemented but not used consistently | Partial gap |
| MODES ARE CONFIG | Partial—some hardcoded behavior | Partial gap |
| FAILED RUNS LEAVE NO CODE | Git checkpoint exists but not enforced | Partial gap |

---

## 2. Key Architectural Issues

### 2.1 Supervisor Does Too Much

The supervisor is a monolith with responsibilities spanning:

- WebSocket chat interface
- Run orchestration (modes → execute → verify → transition)
- Verifier selection and execution
- Sandbox management (local + Sprites)
- File history (undo/redo)
- Git operations (checkpoint, revert)
- Vite dev server management (Docker mode)
- NATS JetStream connection
- Agent harness and tool execution
- Auditor worker (background polling)

**Impact:** Hard to understand, hard to modify, single point of failure.

### 2.2 Data Persistence Is Fragmented

| Store | Persistence | Problem |
|-------|-------------|---------|
| FileHistory | In-memory | Lost on restart; can't undo after restart |
| ArtifactStore | In-memory | Lost on restart; verifier outputs gone |
| AHDB | SQLite | Survives restart but incomplete |
| Sandbox | Ephemeral | Correct for isolation, but no persistence |

**Impact:** File explorer app shows empty state after restart because the agent's working context is lost.

### 2.3 NATS Is Premature Complexity

NATS JetStream is enabled by default with dual-write to SQLite. This adds:

- Complexity in `db.py` (NATS + SQLite paths)
- Additional service dependency (Docker)
- Cognitive overhead understanding event flow

**For single-user mode, NATS is unnecessary.** SQLite is sufficient. NATS becomes relevant only when:
- Multi-device sync is needed
- Multi-tenant knowledge base is built
- Real-time collaboration is required

### 2.4 Mode/Mode Nomenclature Confusion

The codebase uses "mode" throughout (`mode_engine.py`, `mode` field in runs) but the docs refer to:

- "Modes" as deterministic agent configurations
- "Mode transitions" as policy-driven mode selection
- "Modes are configs, not vibes"

**Impact:** New developers (and the original author) are confused about what the system is doing.

### 2.5 Zettelkasten Substrate Is Not Implemented

The imported concepts from `docs/new new/` are not reflected in code:

- Content-addressed objects (hash-based IDs)
- First-class edges (REFERS_TO, DERIVED_FROM, etc.)
- Backlink projection (computed, not stored)
- Promotion workflow (NOTES → SPECS → DOCTRINE)

**Impact:** The knowledge graph reasoning capability (needed for bootstrapping) doesn't exist.

---

## 3. Staged Recommendations

### Stage 1: Simplify Infrastructure (This Week)

**Goal:** Remove premature complexity, establish clear data boundaries.

| Action | Priority | Effort |
|--------|----------|--------|
| Set `NATS_ENABLED=0` by default | High | 1 line |
| Remove NATS dual-write from `db.py` | High | 2-4 hours |
| Persist FileHistory to SQLite | Medium | 4-8 hours |
| Persist ArtifactStore to filesystem | Medium | 2-4 hours |
| Rename "mode" to "mode" in code | Medium | 4-8 hours |

**Deliverable:** Simpler system that works without Docker, remembers state across restarts.

### Stage 2: Complete Auditor Integration (Next 1-2 Weeks)

**Goal:** Unilateral auditor works end-to-end and writes to AHDB.

| Action | Priority | Effort |
|--------|----------|--------|
| Integrate auditor_worker.py with AHDB notes | High | 4-8 hours |
| Connect Writer → /agent/audit endpoint | High | 2-4 hours |
| Store auditor results as typed notes linked to runs | High | 2-4 hours |
| Add basic auditor visualization in UI | Medium | 4-8 hours |

**Deliverable:** User can invoke auditor on files, see results as notes.

### Stage 3: Context Heatmap (2-3 Weeks)

**Goal:** Visualize agent reasoning and file/note relationships.

| Action | Priority | Effort |
|--------|----------|--------|
| Design AHDB query API for relationships | High | 2-4 hours |
| Implement graph query (runs → files → notes → audits) | Medium | 4-8 hours |
| Build React Flow visualization component | Medium | 8-16 hours |
| Connect heatmap to AHDB API | Medium | 4-8 hours |

**Deliverable:** Visual graph showing why the agent made decisions.

### Stage 4: Bootstrapping Foundation (Ongoing)

**Goal:** Enable "Choir within Choir" by making agent reasoning inspectable.

| Action | Priority | Effort |
|--------|----------|--------|
| Query AHDB for mode selection rationale | Medium | 4-8 hours |
| Expose reasoning trace in chat interface | Medium | 4-8 hours |
| Implement basic self-reflection prompts | Low | Variable |
| Add content-addressed object storage (optional) | Low | Future |

**Deliverable:** Agent can explain why it chose a mode or made a decision.

---

## 4. Immediate Technical Recommendations

### 4.1 Rename "Mode" to "Mode"

```python
# Before
from .mode_engine import select_initial_mode, transition_mode

# After
from .mode_engine import select_initial_mode, transition_mode
```

Update all references:
- `run_orchestrator.py`: `mode` field → `mode`
- `db.py`: `mode` column → `mode`
- `verifiers.yaml`: `mode_defaults` → `mode_defaults`
- Frontend: `audit.mode` → `audit.mode`

### 4.2 Simplify db.py NATS Handling

```python
# Conceptual simplification
class EventStore:
    def append(self, event_type, payload, source):
        if NATS_ENABLED:
            self._publish_to_nats(event_type, payload, source)
        self._write_to_sqlite(event_type, payload, source)
```

For now, default to SQLite-only.

### 4.3 Extend EventStore for FileHistory

```python
# Add to EventStore
def save_file_snapshot(self, path: str, content: bytes) -> int:
    """Save a file snapshot for undo."""
    return self.append("file.snapshot", {
        "path": path,
        "content_hash": hash(content),
        # Store content in separate table
    }, source="system")

def get_file_history(self, path: str) -> list[dict]:
    """Get all snapshots for a file."""
    # Query events table
```

### 4.4 Define Clear Service Boundaries

| Service | Responsibility | Data |
|---------|----------------|------|
| **Supervisor** | Run orchestration, modes, AHDB | SQLite (runs, notes, receipts) |
| **API** | Parse, artifacts, auth | Filesystem (artifacts), memory (sessions) |
| **Frontend** | UI, window management, chat | In-memory state, localStorage |
| **Sandbox** | Isolated execution | Ephemeral (local or Sprites) |

---

## 5. What NOT to Do Now

| Item | Reason |
|------|--------|
| Implement content-addressed objects | Complex, not needed for bootstrapping |
| Build multi-tenant knowledge base | Premature, out of scope |
| Add NATS for real-time sync | Single-user mode doesn't need it |
| Implement full zettelkasten substrate | Partial implementation adds confusion |
| Build complex backlink projection | Manual links are acceptable for now |

---

## 6. Success Criteria for Stage 1

- [ ] `./dev.sh` works without Docker/NATS
- [ ] Supervisor starts with `NATS_ENABLED=0`
- [ ] File explorer remembers files after restart
- [ ] Verifiers still run correctly
- [ ] Mode transitions work (no hardcoded "mode" references)
- [ ] Auditor can be invoked and writes results to AHDB

---

## 7. Appendix: Key Files Reference

| File | Purpose |
|------|---------|
| `supervisor/main.py` | Supervisor entry point, WebSocket handler |
| `supervisor/db.py` | EventStore, AHDB, SQLite persistence |
| `supervisor/mode_engine.py` | Mode selection and transition logic (rename to mode_engine.py) |
| `supervisor/run_orchestrator.py` | Run lifecycle: create → execute → verify → transition |
| `supervisor/verifier_runner.py` | Execute verifiers based on mode |
| `supervisor/verifier_plan.py` | Select verifiers by mode + touched paths |
| `supervisor/agent/harness.py` | Agent loop (calls BAML-defined tools) |
| `supervisor/agent/auditor.py` | Unilateral auditor wrapper |
| `supervisor/auditor_worker.py` | Background polling worker (not integrated) |
| `supervisor/file_history.py` | Undo support (in-memory, needs persistence) |
| `api/services/artifact_store.py` | Artifact storage (in-memory) |
| `config/verifiers.yaml` | Verifier definitions and mode defaults |
| `docs/new new/ZETTELKASTEN_SUBSTRATE_SPEC.md` | Content-addressed knowledge substrate |
| `docs/new new/DOCTRINE_SPEC_NOTES_GOVERNANCE_SPEC_zettelkasten_update.md` | Governance model |
| `docs/new new/CHOIR_DOCTRINES_zettelkasten_update.md` | Core doctrines |

---

## 8. Conclusion

ChoirOS has ambitious and well-designed concepts (AHDB, modes, zettelkasten) that are not yet reflected in the implementation. The immediate path forward is simplification:

1. **Pause NATS** — unnecessary complexity for single-user mode
2. **Persist FileHistory and ArtifactStore** — enable continuity across restarts
3. **Rename "mode" to "mode"** — match the docs and clarify intent
4. **Complete auditor integration** — deliver the unilateral auditor feature
5. **Build context heatmap** — enable inspection of agent reasoning

Once these are done, the path to bootstrapping (building Choir within Choir) becomes clearer. The auditor + context heatmap provides the self-reflection capability needed for the agent to reason about its own reasoning.

---

**End of Review**
