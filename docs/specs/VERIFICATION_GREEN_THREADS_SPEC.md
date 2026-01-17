# Verification Green Threads Spec (v0)

This document defines the **verification subsystem** for Choir’s agentic loops.

Core idea:
- **Verification must be in the loop.**
- **Verification must be isolated (“green thread”) to avoid token-noise poisoning.**
- **Raw verifier output is stored as artifacts; only structured attestations enter the control state (AHDB).**

This spec is foundational for agentic run orchestration and nested verification loops.

---

## 1) Motivation

Classic single-loop agents often rely on:
- the agent claiming “done,” and/or
- a human operator stopping the loop.

That is insufficient for:
- trustable autonomy,
- social publishing (ASSERT/PROMOTE),
- adversarial settings (injection/reward hacking),
- and any workflow where approval time dominates execution time.

Therefore:
- **No verifier → no asserted progress.**
- **No asserted progress → no promotion or merge.**

---

## 2) Three-loop architecture

### 2.1 EXECUTION LOOP (run)
Implements changes toward a single WORK ITEM.

### 2.2 VERIFICATION LOOP (Referee)
Runs checks and produces a structured report + ATTESTATION.

### 2.3 GOVERNANCE LOOP (Director / nested loop)
Chooses which verifiers apply, adjudicates results, and decides:
- continue / split / escalate / halt,
- promote / demote assertions,
- and whether to request human approval.

This structure prevents the system from confusing “doing work” with “proving work.”

---

## 3) Verification as “green thread” (subagent isolation)

### 3.1 Why isolation is required
Test output is high-entropy (logs, traces, stack dumps). Feeding raw output back into the main session:
- pollutes the working set,
- induces drift and hallucinated diagnoses,
- burns tokens on irrelevant noise,
- and increases attack surface (prompt injection via logs/content).

Therefore:
- verification runs in an isolated session/context (green thread),
- and only emits compact, typed results.

### 3.2 What enters the main loop
Only these may be injected into the main control state:
- ATTESTATION objects (typed, signed, versioned)
- failure signatures (canonicalized)
- bounded summaries (strict schema)

Raw logs never enter.

---

## 4) Verifier selection policy (agentic, but bounded)

### 4.1 Verifier plan is model-suggested
The director may ask a model to propose a verifier plan.

### 4.2 Verifier plan is policy-bounded
The plan must choose from an allowlist (examples):
- unit tests / integration tests
- lint / typecheck
- build / runtime smoke tests
- UI screenshot diff
- static analysis / security scans
- policy gates (capabilities/no-copy/promotion constraints)

No ad hoc “curl” or arbitrary network activity is considered a verifier.

### 4.3 Mood-sensitive strictness
- CALM: minimal verifiers (fast feedback)
- SKEPTICAL: full verifier suite for target scope
- PARANOID: add negative tests + security gates + independent reruns
- BOLD: broaden coverage after green core

---

## 5) Verification artifacts and attestations

### 5.1 Raw verifier output (artifact)
Raw output is stored as an immutable artifact:
- ArtifactHash
- Tool/Command
- Environment metadata (sandbox id, commit hash, config hash)
- Timestamp

Raw output is not pasted into prompts.

### 5.2 Structured verification report (cheap model)
A low-cost “verifier agent” reads the artifact and emits:

VERIFICATION_REPORT
- VERIFIER_TYPE
- TARGET (work item, files, commit)
- RESULT: PASS | FAIL | FLAKY | INCONCLUSIVE
- FAILURE_SIGNATURES: normalized stack traces / error codes
- SUMMARY: short (bounded)
- NEXT_ACTIONS: 1–3 suggestions (bounded)
- CONFIDENCE: calibrated
- HYPERTHESIS: what this verifier cannot rule out (optional)

### 5.3 ATTESTATION (authoritative)
An ATTESTATION is a content-addressed object referencing:
- the verifier command/config
- the artifact hash
- the report hash
- verifier version
- result

Only attestations can justify ASSERT updates.

---

## 6) Control-state integration (AHDB update rules)

### 6.1 ASSERT updates
- ASSERT may only reference PROMOTED atoms.
- Promotion requires attestations.
- Therefore verifier attestations are a prerequisite for ASSERT.

### 6.2 HYPOTHESIZE updates
If verification fails:
- the system must emit a hypothesis + discriminating test:
  - “what would make this pass next time”
  - “what experiment isolates the failure”

### 6.3 HYPERTHESIS updates
Verifier agents must name blind spots when:
- result is INCONCLUSIVE/FLAKY
- scope is partial (“tests cover only X”)
- environment may be adversarial

Hyperthesis entries are admissible as disclosures but do not authorize action.

---

## 7) Failure handling and replay

### 7.1 Non-monotonic progress triggers
If repeated failures occur with the same signature:
- stop re-running execution blindly
- switch mood to CURIOUS (reframe) or SKEPTICAL (narrow and isolate)
- split the work item until satisfiable

### 7.2 Nested verification for depth
When verification is flaky or ambiguous:
- respawn verifier threads with alternate lenses:
  - clean sandbox rerun
  - isolated test subset
  - additional instrumentation
  - independent checker
This yields more “turns” to reach assertable confidence, without polluting the main loop.

---

## 8) Cost model

- Execution agent: potentially expensive model; bounded by work item.
- Verifier agent: cheap model; job is parsing and structured reporting.
- Director: higher capability, low frequency; decides verifier plan and escalation.

Avoid “race N full rollouts.” Parallelize:
- verification,
- retrieval,
- and adversarial checks.

---

## 9) Security requirements

- Verifier sessions run with minimal privileges.
- Verifier output is treated as untrusted data; no direct execution from it.
- Network egress for verification is off by default; allowlist only if necessary and identity-bound.
- No-copy rule applies: verifier reports must cite by pointer, not paste.

---

## 10) Doctrine block (prompt-ready)

VERIFIER IN THE LOOP IS REQUIRED.
- RAW OUTPUT → ARTIFACT (HASHED)
- GREEN THREAD READS ARTIFACT → REPORT
- REPORT → ATTESTATION
- ATTESTATION UPDATES AHDB (NOT PROSE)

NO VERIFIER → NO ASSERT.
NO ASSERT → NO PROMOTION.
NO PROMOTION → NO GLOBAL EFFECT.
