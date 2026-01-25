# Visualization, UX, and Architecture Ideas for Automation, Iteration, and Customization (v0)

This note enumerates design ideas worth considering. It is intentionally pragmatic: what to build so the system is safe, inspectable, and pleasant while it runs concurrently.

---

## 1) Visualization: what to show (and what not to)

Show the control layer, not the model:
- Active RUNs (one work item each), mode, budget burn, last verifier state
- Capability leases (syscall class, scope, TTL, budget)
- Verifier lanes (green threads): pending/running/completed, attestation results
- AHDB deltas over time (small, surprisal-first)
- Hyperthesis queue (open blind spots) and which runs are consuming them
- Version control state (worktrees/preview branches, commits, discards)
- Local↔global boundary events (publish/promote/attest) when enabled

Do not show:
- raw logs by default (collapse into artifacts)
- raw tool outputs in the main view (noise)
- activation-style “brain” visuals (misleading)

---

## 2) Hierarchical mind map defaults (the “safe overview”)

Default mind map root:
- MACHINE
  - WORK_ITEMS
  - RUNS
  - LEASES
  - VERIFIERS
  - STATE (AHDB / conjectures / hypertheses)
  - VC (worktrees / commits)
  - BUS (topics / inbox)

Design rule:
- First screen must answer: “What is running, what changed, what’s blocked, what’s risky?”

---

## 3) Heat and risk overlays (make invariants visible)

Overlay signals:
- Lethal trifecta risk (private read + net + creds in same zone) → immediate red
- Unverified code pending commit → hard block (not just warning)
- Runs burning budget without AHDB/verifier delta → amber → circuit breaker
- Active NET leases → highlight scope, TTL, bytes
- Flaky verifiers → show failure signature cluster

Use consistent color semantics:
- Green: verified
- Amber: uncertain / in-progress
- Red: policy violation / blocked

---

## 4) Time slider and replay (baseline observability)

A time slider should:
- scrub through event cursor positions
- update the mind map and the narrative summary
- allow “why” click-through: causal chain to receipts and attestations

Even without forking, replay is the core “trust UX.”

---

## 5) UX primitives for iteration (prosumers)

Make these one click:
- CHECKPOINT (auto + manual)
- DIFF (bounded, semantic summary + patch)
- REVERT (atomic)
- PREVIEW (fork workspace) / MERGE / DISCARD
- RUN (start work item) / STOP (kill run) / REQUEUE
- REQUEST_VERIFY (trigger verifier lane)
- ASK_HUMAN (optional lane; later)

Keep text entry small:
- prefer selecting/adjusting AHDB fields over writing long prompts

---

## 6) Customization: skills as desktop apps

Skills should appear as:
- icons/shortcuts
- with typed input forms and output artifact cards
- with visible required capabilities (read/write/net/export badges)

Composition:
- drag-drop skills into workflows (work graph)
- each step is a work item with verifier plan

---

## 7) Architecture: event-driven concurrency without chaos

Patterns:
- queues per mode/lane (execute, research, verify, harden)
- typed messages only (no freeform agent-to-agent DMs)
- leases for syscalls, revocable, scoped, budgeted
- artifact store for raw outputs; only typed summaries enter state
- deterministic projections (AHDB, backlinks, context graph)

Circuit breakers:
- repeated failure signature count
- no-delta budget exhaustion
- runaway daemon detection (token furnace prevention)

---

## 8) “Minimal input” as a UX goal

Optimize for:
- one-line objectives (“30-second demo”)
- AHDB edits (drives/anti-drives; scope constraints)
- selecting verifiers, not narrating plans

Provide “narration on demand”:
- podcast-style summaries of specs/diffs/graphs
- produced as derived artifacts from typed state

---

## 9) Stretch: forking timelines (time travel debugging)

If/when added:
- forks are branches of the event log
- injecting events requires causal invalidation and reflow
- must be visually distinct (timeline branch indicator)
- must have strict budgets (avoid infinite replay compute)

Do not attempt until:
- replay is rock solid
- invariants and leases are enforced reliably

---

## 10) Checklist: what “good” feels like

A user wakes up and sees:
- 1–3 verified commits (or none) with clear attestations
- an updated AHDB delta (small)
- any open hyperthesis clearly listed with bounds
- no unreviewable diffs, no mystery logs, no token furnace
- a single recommended next step (verifiable)
