# Choir 1-Player Headless Automatic Computer (Design v0)

This document specifies the single-player, headless version of Choir: a private, restartable “automatic computer” that runs unattended loops (coding, research, unilateral audits) with strong verification, strict safety boundaries, and mechanical version control. No social layer; no global publication by default.

## 0. Goals and non-goals

Goals
- Run “automatic computer” workloads headlessly (cron/daemon), safely.
- Maintain a small typed control state vector (AHDB + Hyperthesis + Conjecture).
- Produce transactional code changes: verified commits only; failed runs leave no code.
- Isolate token-noisy verification in green threads.
- Crash-safe: can restart from receipts without handoff rituals.
- Local knowledge base compounds; retrieval is pointer-based; no-copy by default.

Non-goals (v0)
- Global social promotion/attestation economics.
- Persistent “agent identities” beyond run IDs and work item IDs.
- Complex multi-tenant permissioning.

## 1. Conceptual model

- SESSION: ephemeral LLM context window.
- RUN: one bounded execution episode (one work item, one mood, budgets).
- WORK ITEM: single objective satisfiable within one run.
- MOOD: deterministic scaffold profile (tools/data/models/verifiers/budgets).
- STATE VECTOR: AHDB (ASSERT/HYPOTHESIZE/DRIVE/BELIEVE), plus HYPERTHESIS and CONJECTURES.
- RECEIPTS: immutable references to what was accessed, what ran, and what changed.

## 2. Components

### 2.1 Control plane (Director service)
Responsibilities
- Select next work item and mood.
- Build the prompt context pack: AHDB + minimal artifacts + evidence pointers.
- Choose verifier plan (policy-bounded).
- Gate commits (director verification).
- Update projections (state vector) from receipts/attestations.

Interfaces
- `plan_next(work_queue_state, ahdb, metrics) -> run_plan`
- `approve_commit(run_id, verifier_attestations, policy_checks) -> decision`
- `apply_spec_change_request(scr) -> accept/reject` (optional v0)

### 2.2 Data plane (Associate runner)
Responsibilities
- Execute one run in an ephemeral worktree/sandbox.
- Produce code diffs and artifacts.
- Run self-verification triggers.
- Emit notes/events and request director verification.
- On failure, discard worktree.

### 2.3 Verification green threads (Verifier runner)
Responsibilities
- Execute verifier commands in isolation.
- Store raw logs as artifacts.
- Produce structured verification reports and ATTESTATION objects.

### 2.4 Storage
- Event log (append-only): run lifecycle events, note events, receipts, decisions.
- Object store (content-addressed): sources, extracts, claims, bindings, conjectures, verifier artifacts.
- Local KB index: embeddings over AHDB/conjecture/hyperthesis objects (not raw content by default).

### 2.5 Scheduler
- Headless daemon/cron that enqueues runs and triggers moods based on guards.
- Event-driven wakeups preferred; optional backoff polling.

## 3. Security and trust zones (1-player)

Invariant: do not co-locate private data + network egress + arbitrary credentials in the same zone.

Zones
- EXECUTION ZONE (CALM/BOLD): repo read/write; network off by default; no ambient credentials.
- RESEARCH ZONE (CURIOUS): network on (allowlisted); local file reads off; identity tokens off or identity-bound.
- VERIFICATION ZONE (SKEPTICAL): runs tests; may read repo; raw logs treated as untrusted data; no network by default.
- HARDENING ZONE (PARANOID): strictest sandbox; policy checks, security scans; quarantine-first behavior.
- PREFERENCE/APPROVAL ZONE (DEFERENTIAL): generates questions or requests explicit human approval (optional in 1-player).

All outbound network must go through a policy-enforced syscall tool (no raw curl).

## 4. Moods (minimum set for v0)

Use at least:
- CALM: execute one bounded step.
- CURIOUS: retrieval / conjecture formation; no code writes by default.
- SKEPTICAL: verification / adjudication; no new feature work.
- PARANOID: hardening / boundary tightening / security checks.
- CONTRITE: crash recovery / projection rebuild.

Mood transitions are deterministic guards based on:
- verifier regressions
- repeated failure signatures
- hyperthesis magnitude
- privilege proximity (commit/publish/export)

(Full palette defined in CHOIR_MOODS_SPEC.md.)

## 5. Control state: AHDB + Hyperthesis + Conjecture

### 5.1 AHDB
- ASSERT: cites only PROMOTED local atoms; must have receipts.
- HYPOTHESIZE: must have discriminating test + budget.
- DRIVE: must have anti-drive.
- BELIEVE: must have update trigger + effect; largely derived from capabilities.

### 5.2 Hyperthesis
- Blind spot boundary: what current verifiers/observer model cannot rule out.
- Must include a bound/mitigation (tighten scope, add verifier, quarantine).

### 5.3 Conjecture
CONJECTURE = (claim, test, edge, ΔO, scope)
Used as the unit of planning and refinement.

## 6. Work graph and “one work item per run”

The director maintains a work queue with:
- work_item_id, description
- acceptance criteria (demo)
- required verifiers
- risk tier
- dependencies
- status

Rule: each run binds to exactly one work item.

If a work item cannot be completed within budget:
- associate emits SPEC_CHANGE_REQUEST or SPLIT_REQUEST as events
- director splits work until satisfiable

## 7. Version control (mechanical) and run output policy

### 7.1 Ephemeral worktrees per run
- create worktree on run start
- all edits occur in worktree
- destroy on failure

### 7.2 Transactional commits
- No commit unless self-verification passes and director approves.
- On failure: reset/delete worktree.
- Notes persist as events (outside git).

(See RUN_OUTPUT_POLICY_SPEC.md.)

## 8. Verification in loop (green threads)

- Verifier commands run in isolated verifier sessions.
- Raw output stored as artifact; never injected into main context.
- Structured report emitted + attestation object created.
- Director consumes attestations to update ASSERT/HYPOTHESIZE and to approve commits.

(See VERIFICATION_GREEN_THREADS_SPEC.md.)

## 9. Notes and docs governance (headless)

Notes are events, not repo files.
- NOTE/OBSERVATION
- NOTE/HYPOTHESIS (with test)
- NOTE/HYPERTHESIS (with bound)
- NOTE/CONJECTURE
- NOTE/REQUEST_HELP
- NOTE/REQUEST_VERIFY

Doc tiers:
- DOCTRINE (rare change)
- SPECS (deliberate change)
- NOTES (free)

Associates may file SPEC_CHANGE_REQUEST events; director merges doc deltas only with evidence.

(See DOCTRINE_SPEC_NOTES_GOVERNANCE_SPEC.md.)

## 10. APIs (headless)

Minimum endpoints (local):
- `POST /run` create run from work item
- `POST /run/{id}/note` append typed note
- `POST /run/{id}/verify` attach verifier attestation
- `POST /run/{id}/commit_request` request director approval
- `POST /work_item` create/split/update work items
- `GET /state/ahdb` current state vector
- `GET /receipts/{id}` fetch receipt pointers

## 11. Observability

Required receipts:
- ContextFootprint
- VerifierResults (artifact pointers + attestations)
- PatchReceipt (diff hash)
- MoodTransition events
- CommitReceipt (commit hash, verifier set, policy decision)

Anomaly triggers:
- repeated identical failure signatures
- repeated runs with no AHDB delta
- unexpected network attempts
- budget exhaustion without progress

## 12. Bootstrapping plan (spiral)

Spiral 1: minimal run loop + work item + ephemeral worktree + one verifier  
Spiral 2: AHDB projection + receipts + restart recovery  
Spiral 3: green-thread verification + no raw logs in main context  
Spiral 4: moods + deterministic transition guards  
Spiral 5: local KB object store + pointer citations + doc governance
