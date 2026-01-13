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
- Multi-provider LLM abstraction (branch)

### Not Started
- Control plane app (separate repo)
- Director/Associate task protocol wiring
- Prompt routing through Director

---

## Phase 0: Ralph-in-Ralph (v0)

**Goal:** Two sandboxes per user. Director plans, Associate executes.

1) **Contracts**
   - DirectorTask and AssociateResult schemas
   - Git actions as Associate tasks

2) **Sandbox orchestration**
   - Spawn Director + Associate via Sprites
   - No secrets inside sandboxes

3) **Prompt flow**
   - Associate UI forwards prompts to Director
   - Director replies only after Associate verification

4) **Time travel**
   - Git checkpoints + reset/checkout tasks
   - No event log, no snapshots

---

## Phase 1: Control Plane (v1)

**Goal:** A trusted app that owns auth and sandbox lifecycle.

- Separate repo with its own CI/CD
- Stable UI (no hot reload)
- Session issuance and token forwarding

---

## Phase 2: Persistence + Replay (v2)

**Goal:** Faster recovery and richer auditing.

- Event log (NATS or equivalent)
- Filesystem snapshots
- Deterministic replay

---

## Phase 3: Publishing (v3)

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
