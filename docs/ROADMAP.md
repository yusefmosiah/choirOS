# ChoirOS Implementation Roadmap

## Current State (Jan 2026)

### What Works
- Web desktop shell (window manager, taskbar, apps)
- FastAPI parsing backend + artifact pipeline
- Supervisor runtime + agent harness (prototype)
- Git checkpoint API + GitPanel UI
- Local dev orchestration via `dev.sh`

### In Progress
- Director/Associate dual-sandbox design
- Sprites integration planning

### Not Started
- Director + Associate sandbox orchestration
- Control plane UI (stable, trusted)
- Git time travel tasks + verification protocol

---

## Phase 3: Ralph-in-Ralph (Now)

**Goal:** Director plans, Associate executes. Two sandboxes per user.

1) **Task contract**
   - DirectorTask and AssociateResult schemas
   - Git actions as Associate tasks

2) **Dual sandboxes**
   - Spawn Director + Associate per user
   - Explicit mounts, zero secrets

3) **Vibecoding**
   - Vite dev server inside Associate
   - Prompt flow: Associate UI -> Director -> Associate

4) **Git time travel**
   - Checkpoints on success
   - Reset/checkout as Associate task types

---

## Phase 4: Persistence + Replay

**Goal:** Fast recovery and time-travel beyond git.

- Event log (NATS or equivalent)
- Filesystem snapshots
- Deterministic replay

---

## Phase 5: Publishing

**Goal:** Artifacts become shareable and attributable.

- Public artifact URLs
- Citation metadata and queries
- Export with provenance

---

## Ordered Checklist (Next Actions)

1. Finalize Director/Associate contract docs
2. Implement Sprites sandbox adapter
3. Split Director and Associate runtimes
4. Wire prompt flow through Director
5. Add git time travel tasks
