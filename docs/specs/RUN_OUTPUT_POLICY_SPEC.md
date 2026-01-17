# Run Output Policy Spec: Verified Code, Evented Notes (v0)

This document formalizes a core SDLC invariant for Choir’s agentic platform:

- **FAILED RUNS LEAVE NO CODE.**
- **ONLY VERIFIED CODE ENTERS GIT.**
- **NOTES ARE TELEMETRY (EVENTS), NOT REPO ARTIFACTS.**

The goal is to maximize trust, reduce review burden, and make the system crash-safe and restartable without accumulating repository noise.

---

## 0) Why this exists

In long-running agentic systems, partial code changes are the primary source of:
- review fatigue (“how long to approve this overnight run?”),
- merge conflicts and drift,
- security risk (unverified side effects),
- and token waste (agents trying to “repair” bad partial states).

The correct posture is:
- Treat code changes as **transactional**.
- Treat progress notes as **append-only telemetry** outside Git.

This makes “Ralph in Ralph” scalable: sessions can crash or restart freely, while durable state stays coherent.

---

## 1) Terms

SESSION
- an ephemeral LLM context window (cattle)

RUN
- one bounded execution episode with exactly one WORK ITEM, one MOOD, and budgets

WORK ITEM
- the single objective of a RUN (must be satisfiable in one session/RUN)

SELF-VERIFICATION
- checks the runner can execute within the RUN sandbox (tests/lints/demos)

DIRECTOR VERIFICATION
- control-plane checks that gate commitment (policy, additional verifiers, risk gates)

NOTES
- progress artifacts (observations/hypotheses/hypertheses/conjectures), stored as events, not files

RECEIPTS
- immutable references to what was accessed, what verifiers ran, and what changed

---

## 2) Two write paths per RUN

### 2.1 CODE PATH (repo/workspace)
Properties:
- mutable during RUN
- must converge to a verified state to persist
- may be discarded entirely on failure

### 2.2 NOTES PATH (event bus / event log)
Properties:
- append-only
- survives resets, crashes, and worktree disposal
- never grants authority by itself
- can later be promoted into SPECS/DOCTRINE via typed change requests

---

## 3) Core invariants (must always hold)

INVARIANT A — Transactional code
- A RUN may only “commit” code if it passes both:
  1) SELF-VERIFICATION
  2) DIRECTOR VERIFICATION

INVARIANT B — Failures are reverted, not repaired in-place
- If verification fails, the system performs:
  - git reset --hard (or discards the worktree)
  - requeues work as a new RUN (possibly split, with updated conjectures)

INVARIANT C — Notes never live in the repo by default
- Notes are written to the event bus/log only.
- Repo is reserved for:
  - code
  - ACTIVE doctrine/spec docs
  - verifier configs/policies
  - optionally, content-addressed receipt blobs (or pointers)

INVARIANT D — No “dirty working tree” escapes
- A RUN ends with either:
  - VERIFIED COMMIT, or
  - CLEAN DISCARD

---

## 4) Evented notes schema (AHDB-typed telemetry)

NOTES are not freeform chat logs. They are typed, small, and queryable.

### 4.1 NOTE event types
- NOTE/OBSERVATION
- NOTE/HYPOTHESIS (must include test + budget)
- NOTE/HYPERTHESIS (blind spot + bound)
- NOTE/CONJECTURE (claim/test/edge/ΔO/scope)
- NOTE/STATUS (heartbeat; mood; progress)
- NOTE/REQUEST_HELP (transformative question)
- NOTE/REQUEST_VERIFY (ask for director verification)

### 4.2 Minimal fields for every NOTE event
- RUN_ID
- WORK_ITEM_ID
- MOOD
- TIMESTAMP
- BODY (structured fields; minimal prose)
- REFERENCES (receipt IDs, diff IDs, evidence set hash)

Notes can be embedded for retrieval and scam detection (later), but the canonical record is structured.

---

## 5) Worktree model (recommended)

To make the invariants cheap:
- each RUN gets an isolated worktree (or ephemeral snapshot)
- the worktree is destroyed on failure
- the worktree is merged/committed only after director approval

This prevents long-lived partial states from accumulating.

---

## 6) Verification gates (what “verified” means)

### 6.1 SELF-VERIFICATION (runner gate)
Required checks depend on MOOD and work type:
- unit tests (targeted)
- lint/typecheck
- minimal demo script (“30-second demo”)
- anti-stub gate
- NO-COPY lint for generated artifacts (if applicable)

If any fail:
- runner must emit NOTE/HYPOTHESIS or NOTE/HYPERTHESIS
- runner must not attempt “repair forever”; it must return control after budget

### 6.2 DIRECTOR VERIFICATION (control-plane gate)
Director may require additional checks:
- broader tests
- policy gates (capabilities, boundaries)
- security scanning
- independent verifier re-run
- diff budget enforcement
- risk-based approval thresholds (DEFERENTIAL mood if needed)

Only the director can authorize a commit.

---

## 7) Commit protocol (success path)

On success:
1) RUN emits NOTE/REQUEST_VERIFY with receipts and verifier results.
2) DIRECTOR enters SKEPTICAL/PARANOID as needed and evaluates.
3) If approved:
   - create commit
   - update work graph state
   - emit COMMIT receipt (hash)
   - update AHDB projection (ASSERT may reference promoted atoms where applicable)

---

## 8) Failure protocol (discard path)

On failure:
1) RUN emits:
   - NOTE/HYPERTHESIS (why it failed / what was blind)
   - NOTE/HYPOTHESIS (what test would settle next)
   - optional SPEC_CHANGE_REQUEST (if docs/spec mismatch caused failure)
2) System performs:
   - git reset --hard OR delete worktree
3) Director decides next:
   - split work item (make it satisfiable)
   - switch mood (CURIOUS/SKEPTICAL/PARANOID)
   - escalate model tier (bounded)
   - request a transformative user input (DEFERENTIAL)

Crucially:
- No partial code is carried forward as “maybe fix later.”

---

## 9) Interaction with docs governance

Notes can propose doc changes but cannot directly mutate ACTIVE specs/doctrine.

Mechanism:
- Associate emits SPEC_CHANGE_REQUEST as an event, with evidence.
- Director adjudicates and merges doc deltas into SPECS (and rarely DOCTRINE).

Docs updates are low-stress because they do not change runtime behavior unless wired into verifiers/policy.

---

## 10) Security rationale

Storing notes outside Git reduces:
- repository pollution and accidental leaks
- prompt injection persistence via committed text
- incentive for agents to smuggle instructions into docs

Typed notes + receipts allow:
- observability and replay
- safe restarts (“never land”)
- postmortems and misconception correction workflows

---

## 11) Summary (prompt-ready)

RUNS ARE TRANSACTIONS.
- IF VERIFIED → COMMIT
- IF NOT VERIFIED → DISCARD

NOTES ARE EVENTS.
- ALWAYS APPEND
- NEVER BLOCK
- NEVER AUTHORIZE PRIVILEGE

ONLY THE DIRECTOR CAN COMMIT.
