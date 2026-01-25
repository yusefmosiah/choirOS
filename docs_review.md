# ChoirOS Deep Review: Current State, Vision, Contradictions, and Path Forward

**Date:** 2026-01-23  
**Status:** Active review document (consolidated from multiple reviews)

---

## Executive Summary

ChoirOS is in a **"hybrid" state** between a standard agent harness and the "Automatic Computer" vision. It has a sophisticated execution engine but the core "OS" invariants aren't yet enforced.

**Working ("Walking Skeleton"):**
- ✅ Event-sourced core (NATS/SQLite append-only log)
- ✅ Sandboxed execution with git-based rollback
- ✅ Transactional run → verify → checkpoint lifecycle
- ✅ Mode-based capability gating (8 modes, budgets defined)
- ✅ BAML-powered agent planning and verification analysis
- ✅ AHDB state vector projected and injected into prompts

**Half-way:**
- ⚠️ Artifacts folder exists but not a unified content-addressed store (CAS)
- ⚠️ Agent reads AHDB but lacks `propose_ahdb` tool to update its own register
- ⚠️ Machine class exists but is thin wrapper over orchestrator
- ⚠️ run_notes in DB but not yet "30-second summary" streams

**Missing (core "OS" claim):**
- ❌ AHDB-driven mode selection (guards not wired)
- ❌ Receipts-as-authority enforcement
- ❌ Background lanes / work queue
- ❌ Context Graph for replay/visualization
- ❌ AgentFS as canonical filesystem

---

## 1. What's Implemented vs. Specced

### A. Machine Control Plane

| Aspect | Implemented | Specced (Jan 23 docs) | Gap |
|--------|-------------|----------------------|-----|
| Single-writer scheduling | ✅ `_writer_lock` works | ✅ | None |
| Mode selection | ❌ Stubbed: always CALM | AHDB + guards | `_select_mode` has TODO |
| Work queue | ❌ Not implemented | Non-blocking UI queue | Command bar blocks |
| NATS directive handling | ✅ Best-effort | Canonical event-driven | NATS optional |

### B. Run Lifecycle & Verification

| Aspect | Implemented | Specced | Gap |
|--------|-------------|---------|-----|
| Execute → Verify → Checkpoint | ✅ Works | ✅ | None |
| Rollback on failure | ✅ Works | ✅ | None |
| BAML task assessment | ✅ Works | ✅ | None |
| Verifier → AHDB promotion | ❌ Manual only | Auto via receipts | **Key gap** |

### C. Modes ("Modes")

| Aspect | Implemented | Specced | Gap |
|--------|-------------|---------|-----|
| 8 modes defined | ✅ `mode_config.py` | ✅ | None |
| Tool allowlists | ✅ Works | ✅ | None |
| Budget enforcement | ⚠️ Defined, not enforced | Strict budgets | Not enforced at runtime |
| Terminology | ❌ Mixed mode/mode | Consistent | DB column `mode`, events use `mode` |

### D. AHDB (State Vector)

| Aspect | Implemented | Specced | Gap |
|--------|-------------|---------|-----|
| Tables exist | ✅ state/deltas/proposals | ✅ | None |
| Proposal → Assert flow | ⚠️ Manual `promote_ahdb_proposals` | Auto via verifier receipts | Not wired |
| Evidence pointers | ❌ Not implemented | Required for assertions | Missing fields |
| Injection into prompts | ✅ `ModePromptBuilder` | ✅ | None |

### E. Event Sourcing

| Aspect | Implemented | Specced | Gap |
|--------|-------------|---------|-----|
| SQLite event log | ✅ Works | Projection only | **Contradiction** |
| NATS publishing | ⚠️ Best-effort | Canonical source | Not reliable |
| Replay/projection rebuild | ❌ Not implemented | Required | No projector |
| Event contract | ✅ Defined | ✅ | Payload schemas loose |

---

## 2. Key Contradictions (Docs vs. Code)

### Contradiction 1: Source of Truth

**Spec says:** "NATS is canonical event log; SQLite is projection only" (CHOIR_MACHINE_V0_SPEC.md)

**Code does:** SQLite is the reliable write path; NATS is optional best-effort publish

```python
# db.py docstring claims NATS canonical, but reality:
NATS_ENABLED = NATS_AVAILABLE and os.environ.get("NATS_ENABLED", "1") == "1"
# And NATS publish failures are silently logged, not blocking
```

**Impact:** Replay, recovery, and "continuous compute" cannot be reliable until resolved.

### Contradiction 2: Mode vs. Mode Terminology

| Location | Uses |
|----------|------|
| `supervisor/mode_engine.py` | `MODE_CALM`, `ModeInputs` |
| `supervisor/db.py` (runs table) | Column: `mode` |
| `supervisor/run_orchestrator.py` | Parameter: `mode` |
| `supervisor/event_contract.py` | Event types: `mode.start`, `mode.stop` |
| `supervisor/machine.py` | Payload field: `mode` (falls back to `mode`) |
| `supervisor/auditor_worker.py` | Emits: `mode` field |

**Impact:** Projections/visualizations will mis-join runs, directives, and audits.

### Contradiction 3: AHDB Authority Rules (Paper vs. Code)

**Spec says:** "Only receipt-backed deltas can be asserted; LLM output is never authority"

**Code does:**
```python
# machine.py - promote_ahdb_proposals
def promote_ahdb_proposals(self, run_id: str) -> int:
    proposals = self.store.list_ahdb_proposals(run_id)
    for proposal in proposals:
        if proposal.get("status") != "proposed":
            continue
        delta = proposal.get("delta")
        # No verification check! Just promotes.
        self.store.log_ahdb_delta(delta, {"run_id": run_id, "authority": "asserted"})
```

**Impact:** AHDB either becomes meaningless or requires manual babysitting.

### Contradiction 4: Event-Driven vs. Polling

**Spec says:** "Event-driven lanes consume events; scaling = higher event rate"

**Code does:** Auditor polls SQLite every 2 seconds
```python
# auditor_worker.py
while self.running:
    new_events = self.store.get_events(since_seq=self.last_seq, limit=10)
    # ...
    await asyncio.sleep(2)  # Polling, not event-driven
```

### Contradiction 5: AgentFS as Canonical Filesystem

**Spec says:** "AgentFS is canonical sandbox filesystem; cross-mode sharing via artifacts only"

**Code does:** Repo working directory is de facto canonical; sandbox used only for verifiers

### Contradiction 6: "No Privilege Without Receipts"

**Doctrine says:** Receipts must be checked before authorizing next step in Machine

**Code does:** Receipts are emitted but nothing checks them before proceeding

### Contradiction 7: Self-Dev Paradox

**Doctrine says:** "Failed runs leave no code"

**Reality:** Without Context Graph, debugging failures is hard—you need to see what happened, but the thing that shows you what happened isn't built yet

---

## 3. Primary Obstacles to the Vision

### Obstacle 1: No Single Authoritative Substrate

Two "almost canonical" substrates exist:
- SQLite events + projections (canonical in practice for events)
- Repo filesystem (canonical for code state)

NATS and sandbox checkpoints exist but aren't authoritative.

**Why it blocks:** Visualization/replay, background lanes, and verification-as-authority all require "I can reconstruct what happened."

### Obstacle 2: Authority Pipeline Not Enforced

The key invariant (*LLM output ≠ authority; only receipts are*) isn't enforced:
- Verifiers run and store results
- AHDB proposals exist
- But nothing ties them together automatically

**Why it blocks:** Either manual promotion (slow) or unsafe auto-promotion (breaks trust).

### Obstacle 3: Missing Scheduler Primitives

Machine has a writer lock but lacks:
- Real work queue for UI to enqueue into
- Prioritization (verify/anomaly > feature work)
- Rate limits / budgets per lane
- Cancellation/preemption

**Why it blocks:** Background agency becomes "concurrent chaos" without queue + backpressure.

### Obstacle 4: Inconsistent Vocabulary and Event Payload Schemas

- mode vs. mode
- Event types normalized, but payload schemas aren't rigid
- Linking fields (`work_item_id`, `run_id`, `session_id`) not uniformly present

**Why it blocks:** Cannot build legibility (graph, receipts, time slider) if linking keys are inconsistent.

---

## 4. Recommended Path Forward

### Phase 0: Decide Truth + Normalize Terminology (S–M: 1–3h)

1. **Pick SQLite-first as canonical for v0**
   - Update CHOIR_MACHINE_V0_SPEC.md to match reality
   - Reframe NATS as "optional transport / replication"
   
2. **Normalize terminology: use "mode" everywhere**
   - Keep DB column `runs.mode` temporarily (migration later)
   - Event payloads always emit `mode`, never `mode`
   - Add `mode` alias in reads for backward compatibility

### Phase 1: Close the AHDB Loop (M: 1–3h)

**Two parts:**

**A. Wire Verifier → Receipt → AHDB Promotion:**

1. When `RunOrchestrator` completes verifiers:
   - Emit typed receipt event: `receipt.verifier.attestations`
   - Include `run_id`, verifier IDs, statuses, artifact pointers

2. Change `Machine.promote_ahdb_proposals`:
   - Require `run.status == "verified"` before promotion
   - Link to evidence (`run_id` + receipt seq)

3. When promoting:
   - Write `receipt.ahdb.delta` with `authority="asserted"`

**B. Add `propose_ahdb` tool to AgentTools:**

The agent currently reads AHDB but cannot formally propose updates. Add:
```python
# In supervisor/agent/tools.py
def propose_ahdb(self, field: str, value: dict, evidence: list[str]) -> dict:
    """Propose an AHDB update (ASSERT/HYPOTHESIZE/DRIVE/BELIEVE)."""
    self.store.create_ahdb_proposal(
        run_id=self.current_run_id,
        delta={field: value},
        evidence=evidence,
    )
    return {"status": "proposed", "field": field}
```

This closes the loop: agent proposes → verifier validates → Machine promotes.

### Phase 2: Make Work Queue Real (M–L: 1–2d)

1. Treat `work_items` table as the queue
   - UI enqueues with `status=queued`
   - Machine loop claims next runnable item

2. Add scheduler loop:
   - Respects single-writer lock
   - Emits `mode.start` from queue (not directly from prompt)

3. `/agent` WebSocket returns immediately with "enqueued" + work item ID

### Phase 3: Context Graph v0 / Legibility (L: 1–2d)

Start with **time-sliced event projection** (simple version of Context Graph):

**Nodes:**
- work_item, run, mode events, verifier results, AHDB deltas, file.write, artifacts

**Edges:**
- run→work_item, receipts→run, deltas→run, artifacts→receipt

**Key requirements:**
1. **Consistent linking keys** (ensure every event includes `run_id`)
2. **Simple time-slice query**: "show me what happened in the last run"
3. **30-second summary stream**: surface run_notes as legible progress

This breaks the **Self-Dev Paradox**: you can now debug failed runs by replaying the context graph.

### Phase 4: Promote Machine OS (M–L: 1–2d)

Move ModeEngine logic into Machine and make it the primary entry point:
- Machine becomes the scheduler, not just a wrapper
- Mode guards driven by AHDB state + receipts
- All execution flows through Machine (not direct orchestrator calls)

### Phase 5: AgentFS + Event-Driven Lanes (XL, defer)

Only after above is stable:
- Decide canonical filesystem model (AgentFS as CAS)
- Move auditor to event consumption (not polling)
- Add leases, rate limits, circuit breakers
- Resolve NATS/SQLite divergence for complex projections

---

## 5. Immediate Doc Cleanup Tasks (The "Haircut")

### Terminology Harmonization (High Priority)

1. **Global rename: mode → mode** in code comments and new code
   - Keep `mode_engine.py` filename (rename later)
   - Keep DB column `runs.mode` (migration later)
   - All new event payloads use `mode`

2. **Retire "Phase 3 Agent Platform" language**
   - Replace with "Automatic Computer" / "Machine OS" in docs

### Doc Updates

3. **Update docs/00_INDEX.md**
   - Add glossary section defining mode/mode relationship
   - Surface Jan 23 concepts (AHDB, Context Graph, Machine)

4. **Update docs/ARCHITECTURE_OVERVIEW.md**
   - Add storage/data-flow notes matching current_architecture_jan23

5. **Update docs/current_architecture_jan23.md**
   - Add banner: "Snapshot as of 2026-01-23; for stable overview see ARCHITECTURE_OVERVIEW.md"

6. **Update docs/specs/CHOIR_MACHINE_V0_SPEC.md**
   - Change "NATS is canonical" to "SQLite-first for local dev; NATS for optional replication"

7. **Update progress.md**
   - Fix "modes are now modes" to clarify terminology relationship

---

## 6. Tests Passing (Verified)

```
supervisor.tests.test_event_contract
supervisor.tests.test_ahdb_projection  
supervisor.tests.test_runs
supervisor.tests.test_machine
supervisor.tests.test_mode_engine
```

All 22 tests pass. NATS publish warnings are expected (disabled in tests).

---

## 7. File Locations for Key Components

| Component | File |
|-----------|------|
| Machine control plane | `supervisor/machine.py` |
| Run orchestrator | `supervisor/run_orchestrator.py` |
| Mode configurations | `supervisor/mode_config.py` |
| Event store + projections | `supervisor/db.py` |
| Event contract | `supervisor/event_contract.py` |
| Agent harness | `supervisor/agent/harness.py` |
| Verifier runner | `supervisor/verifier_runner.py` |
| Auditor worker | `supervisor/auditor_worker.py` |
| NATS client | `supervisor/nats_client.py` |
| Mode engine | `supervisor/mode_engine.py` |

---

## 8. Key Insight: The "Walking Skeleton" is Real

The good news: ChoirOS has a **working transactional execution engine**. The run→verify→checkpoint loop works. BAML integration works. Mode gating works.

The gap isn't "nothing works"—it's that the **OS invariants aren't enforced**:
- Receipts are emitted but not checked
- AHDB is read but not updated by the agent
- Machine exists but doesn't schedule

The path forward is **wiring**, not **rebuilding**. Each phase connects existing pieces:
1. Verifier results → AHDB promotion (wiring)
2. Work items → Machine scheduler (wiring)
3. Events → Context Graph (wiring)

This is why the effort estimates are hours/days, not weeks.
