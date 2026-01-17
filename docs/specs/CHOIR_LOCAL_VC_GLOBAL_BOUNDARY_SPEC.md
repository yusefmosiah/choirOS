# Choir Local VC + Global Promotion Boundary Spec (v0)

This document specifies the missing coupling between:
- **Per-user runs** (private vibecoding, research, unilateral audits), and
- **Multi-user social epistemics** (ASSERT / ATTEST / PROMOTE as global KB behaviors).

The key architectural move is a strict boundary:
- **Local workspaces evolve safely under local version control,**
- **Global Choir state changes only via explicit publish/promote/attest actions.**

---

## 1) Two planes (must not be conflated)

### Plane A — PRIVATE COMPUTE (per-user)
Scope:
- RUNS (unilateral audit runs, coding loops, research loops)
- User workspace filesystem
- Local KB (private)
- Local AHDB state vector + receipts + conjectures/hypertheses

Properties:
- crash-safe and restartable
- no implicit sharing
- fast iteration
- strict sandboxing / capability modes
- local checkpoints and rollback

### Plane B — SOCIAL EPISTEMICS (multi-user)
Scope:
- Global public artifacts (published)
- GLOBAL ASSERT / ATTEST / PROMOTE
- Topic streams, challenge windows, TWP/CHIPS economics (later)

Properties:
- adversarial
- contestable
- authority gated (promotion, attestations)
- delayed finality (vesting/slashing)
- independent reuse is the main reward signal

---

## 2) Terminology (clarifying “assert/promote/attest”)

In v0 and early v1, implement these **locally** first:

LOCAL-ASSERT
- a claim is admissible within the user’s workspace/KB

LOCAL-ATTEST
- verifier outputs and receipts that justify local assertions

LOCAL-PROMOTE
- elevate quarantined local objects to local canonical memory

Later, add global behaviors as separate verbs:

PUBLISH
- explicit export of a local object (or a redacted projection) to public scope

GLOBAL-PROMOTE
- collateralized move to make a public object ASSERT-eligible in global KB

GLOBAL-ATTEST
- third-party verification work on public objects

Rule:
- **No global state change without explicit PUBLISH.**

---

## 3) Local mechanical VC for the web desktop OS (must-have)

### 3.1 Why
If the desktop live-updates code/files, non-experts need safety primitives.
This must be simpler than Git UX, but it must have Git-like semantics.

### 3.2 Minimal primitives (v0)
CHECKPOINT
- create a snapshot of workspace state (files + metadata) with an ID

DIFF
- show changes since last checkpoint (file list + patch)

REVERT
- revert workspace to a selected checkpoint (atomic)

PREVIEW (branch/worktree)
- create an isolated workspace fork for risky runs
- merge/discard explicitly

SAFE APPLY
- stage changes → run verifiers → checkpoint → apply
- if verifiers fail, do not apply to main

### 3.3 UI surface (web desktop)
Expose as a timeline rail:
- checkpoints as cards (timestamp, mood, demo status, verifier results)
- one-click “undo to checkpoint”
- “create preview workspace”
- “merge preview” / “discard preview”

Do not expose Git concepts by default; allow “advanced” view.

---

## 4) Local epistemic VC (semantic level, parallel to mechanical VC)

Local knowledge objects have lifecycle states:
UNTRUSTED → QUARANTINED → PROMOTED (local) → RETRACTED (local)

Rules:
- LOCAL-ASSERT may cite only PROMOTED local atoms
- Promotion requires local attestations (verifiers) and receipts
- Retractions remain in history; they flip admissibility

This mirrors the global pipeline but stays private.

---

## 5) Run model (private plane)

RUN is the unit of compute:
- one WORK ITEM (one objective)
- one MOOD configuration (tools/data/models/verifiers/budgets)
- produces receipts and state deltas
- costs CHIPS (credits) locally

RUN outputs are quarantined by default; they become locally asserted only after local promotion.

---

## 6) Crash-safe “never land” semantics (private plane)

The system should not require graceful session endings.
Instead:

- Continuous status events (“heartbeats”) are emitted
- AHDB is stored as a live projection
- Work items are idempotent and requeueable
- On restart, CONTRITE mood rebuilds state from receipts

Landing the plane becomes optional hygiene, not correctness.

---

## 7) Explicit export path to global (social plane)

### 7.1 Publish is explicit
PUBLISH is a user-triggered syscall:
- select artifacts / atoms to export
- optionally redact (private dependencies remain private)
- assign license/visibility
- compute content hashes
- create public object references

Publishing must be reversible:
- unpublish hides future retrieval but preserves integrity receipts (for disputes)

### 7.2 Global promotion is voluntary
Global PROMOTE requires collateral (stake) and opens challenge windows.
Wallet size does not rank; TWP governs yield.

### 7.3 Global attestation is subscribable
Topic streams route new public objects to attesters.
Attesters spend CHIPS to produce attestations; rewards vest based on survival and reuse.

---

## 8) Hard separation from platform repo/CI/CD

There are two mechanically separate repo classes:

PLATFORM REPO
- Choir OS, agent harness, verifiers, services, UI
- CI/CD pipeline, releases, migrations

USER WORKSPACE REPO
- user projects, private workspaces, preview branches
- no automatic propagation to platform

Rules:
- user workspace changes never affect platform deployment
- platform updates are versioned and rolled out independently
- platform upgrades may require compatibility shims for local data formats

---

## 9) Security and trust zones (local-first)

The local plane must enforce the “lethal trifecta” constraint:
- do not co-locate private data + network + credentials in one trust zone

Operationalization:
- web/KB research runs in CURIOUS subagent/mood in a separate sandbox
- execution runs in CALM/BOLD with network off by default
- export/publish requires DEFERENTIAL (approval) and policy tokens

---

## 10) Implementation checklist (v0)

1) Local workspace checkpointing: CHECKPOINT/DIFF/REVERT
2) Preview workspaces: PREVIEW/MERGE/DISCARD
3) Receipt emission: every tool call and verifier writes receipts
4) Local object lifecycle: quarantine/promote/retract (local)
5) Explicit PUBLISH syscall (no implicit global writes)
6) Two-repo separation: platform vs user workspaces
7) Mood gating for network/exfiltration primitives

---

## 11) “Land the plane” for this thread (handoff)

The practical, memetic summary:
- RUNS are per-user.
- ASSERT/ATTEST/PROMOTE are social behaviors only after explicit PUBLISH.
- Local VC keeps live updates safe.
- AHDB is the state vector that persists across crashes and drives the loop.
- Global is opt-in, collateralized, and contestable.

This boundary lets Choir ship as a prosumer “automatic computer” first, and become a social epistemic market later, without mixing the risks.
