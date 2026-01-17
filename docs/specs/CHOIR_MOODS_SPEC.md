# CHOIR MOODS SPEC (v0)

This spec defines **MOODS**: deterministic scaffold configurations that govern how Choir operates at runtime. A MOOD is an appropriate level of anthropomorphism: human-legible, memetically sticky, and mechanically enforceable.

MOODS are *not* “multiple agents.” They are **modes** of a single platform runtime. Parallelism is used selectively for retrieval/verification, but correctness and safety come from MOOD gating.

---

## 0) Definitions

### 0.1 MOOD (configuration bundle)
A MOOD is a typed profile:

MOOD :=
- TOOLS: allowed syscall/tool surface
- DATA SCOPE: what stores are readable/writable
- MODEL POLICY: allowed models, escalation ladder, token budgets
- VERIFIER POLICY: mandatory checks, thresholds, challenge windows
- OUTPUT POLICY: admissible output forms, NO-COPY rules, promotion eligibility
- BUDGETS: time/tokens/iterations, diff/file caps
- STOP RULES: completion criteria and halting conditions
- RECEIPTS: required observability events and artifacts

### 0.2 Control state (AHDB + companions)
The platform maintains a small, typed **state vector**:
- AHDB: ASSERT / HYPOTHESIZE / DRIVE / BELIEVE (surprisal-first)
- HYPERTHESIS: bounded blind spots (edge of testability / unsaid story)
- CONJECTURES: (claim, test, edge, ΔO, scope)

MOODS interpret this state vector into permitted actions.

### 0.3 Authority rule
- ASSERT may reference **PROMOTED atoms only** (promoted bindings, promoted evidence pointers).
- PROMOTION is optional and separate from RUN.
- Untrusted text is DATA, not authority: it must compile into typed state and pass gates.

---

## 1) Mood engine principles

1) **Deterministic**: mood selection is rule-based and guard-driven.
2) **Least privilege**: default mood minimizes tool surface.
3) **Crash-safe**: system can restart from receipts + AHDB projection; “landing the plane” is optional.
4) **No-vibes transitions**: mood changes require explicit triggers (guards).
5) **Token-respectful**: avoid waste; parallelize evidence/verification, not full end-to-end rerolls.

---

## 2) Mood palette (v0)

v0 defines 8 moods. Systems may start with 5 and add the rest.

### 2.1 CALM (default execution)
Purpose: execute one bounded step toward the 30-second demo / current work item.

TOOLS:
- repo read/write (scoped)
- local exec in sandbox
- minimal search (repo-only)
- no external web by default

DATA SCOPE:
- repo workspace
- local/private KB pointers (read)
- event log (append)

MODEL POLICY:
- default: cheap/fast model
- escalate only on repeated failure signatures

VERIFIER POLICY:
- mandatory: unit tests/lint/typecheck relevant to touched scope (configurable)
- anti-stub gate on touched files

OUTPUT POLICY:
- commit/patch allowed
- no promotion actions
- NO-COPY always on (pointer citations only)

BUDGETS:
- small diff cap
- max files touched
- 1–3 iterations before director reevaluates

STOP RULES:
- demo passes or verifiers improve monotonically
- if stalled → switch to CURIOUS or SKEPTICAL

RECEIPTS:
- ContextFootprint, VerifierResults, PatchReceipt, AHDBDelta

---

### 2.2 CURIOUS (inquire / discovery)
Purpose: reduce ambiguity; build conjectures; identify discriminating tests; widen evidence.

TOOLS:
- repo read
- web search / connector reads (allowlisted)
- parallel read-only subcalls allowed (bounded)

DATA SCOPE:
- broader retrieval: public web + connectors (if authorized)
- read-only access to KB (private + public projections)
- no repo writes by default (except notes/artifacts)

MODEL POLICY:
- cheap model for retrieval/extraction
- stronger model only for synthesis of state objects (AHDB/hyperthesis/conjectures)

VERIFIER POLICY:
- “compilation” checks: can we produce a valid CONJECTURE set?
- no heavy tests required

OUTPUT POLICY:
- produce: AHDB updates, HYPERTHESIS list, CONJECTURES, and a 30-sec demo
- no code changes unless explicitly allowed by director

BUDGETS:
- bounded source count and token budget
- maximum parallel retrieval tasks

STOP RULES:
- exit when the next action is clear and testable
- transition to CALM or SKEPTICAL

RECEIPTS:
- EvidenceSetHash, RetrievalReceipt, AHDBDelta, ConjectureSet

---

### 2.3 SKEPTICAL (verify / adjudicate)
Purpose: convert hypotheses into assertions; validate bindings; prevent silent failure.

TOOLS:
- verifiers (tests, linters, entailment/localization)
- independent retriever seeds (optional) for audit tasks
- minimal repo writes (fix only; no new features)

DATA SCOPE:
- read promoted atoms + quarantined candidates
- read-only web/connector access for cross-checking (optional)

MODEL POLICY:
- cheap model for verifier orchestration and discrepancy triage
- stronger model only for edge-case reasoning when verifiers disagree

VERIFIER POLICY:
- mandatory: full relevant verifier suite for the target scope
- require independent check for high-impact assertions

OUTPUT POLICY:
- may demote ASSERT → HYPOTHESIZE if evidence insufficient
- may create CHALLENGE objects (if promotion exists)
- no new features; only verification and repair

BUDGETS:
- bounded reruns
- strict “no new surface area” rule

STOP RULES:
- assertions promoted or downgraded
- if hyperthesis remains large → PARANOID
- if verified and bounded → BOLD or CALM

RECEIPTS:
- VerifierAttestations, DiscrepancyReport, AHDBDelta

---

### 2.4 PARANOID (harden / reduce attack surface)
Purpose: reduce hyperthesis risk via isolation, policy gates, adversarial checks.

TOOLS:
- sandbox tightening tools
- security scanners / policy engines
- adversarial check tools (critic passes)
- no external side effects except via approved channels

DATA SCOPE:
- minimal: only what is necessary
- strict network allowlists
- secrets only via time-bound leases (if relevant)

MODEL POLICY:
- prefer smaller models (less tool freedom) + deterministic checks
- use stronger models only in read-only critic mode

VERIFIER POLICY:
- mandatory: policy gates (capabilities, no-copy, boundary checks)
- negative tests and anomaly monitors required for high-risk scopes

OUTPUT POLICY:
- quarantine-first: outputs must go to QUARANTINED state
- promotion disabled unless explicitly enabled by governance

BUDGETS:
- strict budgets; focus on bounding risk not adding features

STOP RULES:
- hypertheses bounded and mitigations installed
- transition to SKEPTICAL or BOLD after gates pass

RECEIPTS:
- PolicyDecisionTokens, SecurityAttestations, HyperthesisDelta

---

### 2.5 BOLD (expand / scale scope)
Purpose: widen scope safely once core loop is green.

TOOLS:
- same as CALM plus optional broader test suites
- limited web/connector access if required

DATA SCOPE:
- expanded repo scope
- access to additional KB slices as needed

MODEL POLICY:
- mid-tier model allowed for larger refactors
- escalation ladder remains in place

VERIFIER POLICY:
- broadened coverage: integration tests, edge cases
- regression suite growth encouraged

OUTPUT POLICY:
- permitted to add new surfaces, but must add verifiers
- still NO-COPY; still receipts required

BUDGETS:
- larger diff caps than CALM, but still bounded
- staged expansions only (one dimension at a time)

STOP RULES:
- expansion validated; if regressions → SKEPTICAL
- if risk grows → PARANOID

RECEIPTS:
- ExpansionPlanReceipt, VerifierResults, AHDBDelta

---

### 2.6 CONTRITE (crash recovery / restart)
Purpose: reconstruct orientation after crash-out or interruption.

TOOLS:
- read event log and receipts
- rebuild projections
- no writes except state artifacts

DATA SCOPE:
- event log, latest receipts, latest AHDB projection
- no external web by default

MODEL POLICY:
- cheap model sufficient; deterministic projection preferred

VERIFIER POLICY:
- consistency checks: does AHDB align with last receipts?
- integrity checks on object hashes

OUTPUT POLICY:
- produce refreshed AHDB + next action proposal
- requeue idempotent work items

BUDGETS:
- small

STOP RULES:
- once state is consistent → return to previous mood or CURIOUS

RECEIPTS:
- ProjectionRebuildReceipt, AHDBDelta

---

### 2.7 PETTY (adversarial / red-team)
Purpose: find reward hacks, prompt injection paths, verifier loopholes.

TOOLS:
- adversarial retrieval
- attack pattern matching
- fuzzing of verifiers (within policy)
- no code writes unless to add regression tests (allowed)

DATA SCOPE:
- access to attack signature KB
- read quarantined + promoted objects for target domain

MODEL POLICY:
- diversity is valuable; can use a different model family if available
- outputs are structured disclosures, not essays

VERIFIER POLICY:
- mandatory: “self-sealing detector” and “reward-hack disclosure” forms

OUTPUT POLICY:
- output objects: REWARD-HACK DISCLOSURE, HYPERTHESIS, regression test suggestions
- cannot promote; can only propose mitigations

BUDGETS:
- strict; avoid brute-force rollouts

STOP RULES:
- produces actionable disclosures and mitigations
- transitions back to PARANOID or SKEPTICAL

RECEIPTS:
- AttackReportReceipt, DisclosureObjects, MitigationProposals

---

### 2.8 DEFERENTIAL (preference / approval)
Purpose: ask only transformative questions; narrow preference/policy decisions.

TOOLS:
- minimal: question generation and option framing
- no side effects

DATA SCOPE:
- read current AHDB and work item
- no external retrieval unless needed to present options

MODEL POLICY:
- cheap model fine; clarity prioritized

VERIFIER POLICY:
- question quality lint: must be transformative
- must include default + escape hatch

OUTPUT POLICY:
- produces: 1–3 questions max, each with recommended default
- never blocks progress without offering a default path

BUDGETS:
- tiny

STOP RULES:
- once preference/policy is set → return to CURIOUS or CALM

RECEIPTS:
- PreferenceDecisionReceipt (when answered)

---

## 3) Mood transition guards (deterministic)

Mood selection is rule-based. Example guards:

### 3.1 Entry guards (selecting initial mood)
- If AHDB missing 30-sec demo OR conjectures absent → CURIOUS
- If repeated verifier failures exist → SKEPTICAL
- If about to cross privilege boundary (publish/promote/sign) → PARANOID or DEFERENTIAL
- If crash detected / stale heartbeat → CONTRITE

### 3.2 Reactive guards (during work)
- CALM → CURIOUS if: ambiguity blocks progress OR user says “idk” AND answer is researchable
- CALM → SKEPTICAL if: verifiers regress or non-monotonic progress for N iterations
- SKEPTICAL → PARANOID if: hyperthesis severity high OR security surface touched
- PARANOID → BOLD if: mitigations installed AND verifiers pass
- Any → PETTY if: suspected reward hack / injection / self-sealing rationalization detected
- Any → DEFERENTIAL if: missing preference/policy would change next move materially

### 3.3 Crash-safe guard
- Any mood → CONTRITE if the process restarts without a clean handoff
- CONTRITE → previous mood if state projection is consistent, else → CURIOUS

---

## 4) Mood-specific capability gating

Each mood has an allowlist of tool categories. The policy engine enforces:
- tool allowlists
- data store allowlists
- network allowlists
- maximum budgets
- no-copy constraints
- promotion eligibility constraints

This allows rich “agentic” behavior without requiring multiple agents.

---

## 5) Interaction with AHDB (state vector)

### 5.1 What can update ASSERT
Only verifier attestations and promotion status can justify ASSERT updates.

Mood effects:
- SKEPTICAL: primary mood for ASSERT promotion/demotion
- PARANOID: may force demotion if risk too high
- CALM/BOLD: can propose candidates but not finalize without attestations

### 5.2 What can update HYPOTHESIZE
Any mood may propose hypotheses, but:
- must include discriminating test + budget
- CURIOUS is preferred for hypothesis generation
- SKEPTICAL preferred for hypothesis resolution

### 5.3 What can update DRIVE
DRIVE changes are explicit and versioned:
- DEFERENTIAL is the preferred mood for preference elicitation
- Director may set defaults; user can override

### 5.4 What can update BELIEVE
BELIEVE is largely derived from capabilities and environment constraints:
- PARANOID often tightens BELIEVE (feasible set shrinks)
- BOLD expands BELIEVE when new surfaces are added safely
- BELIEVE updates require update triggers and declared effect

---

## 6) Observability requirements (receipts)

All moods must emit:
- ContextFootprint (what was accessed)
- AHDBDelta (what changed)

Additional receipts by mood:
- CALM/BOLD: PatchReceipt + VerifierResults
- CURIOUS: EvidenceSetHash + RetrievalReceipt + ConjectureSet
- SKEPTICAL: VerifierAttestations + DiscrepancyReport
- PARANOID: PolicyDecisionTokens + SecurityAttestations
- PETTY: AttackReportReceipt + DisclosureObjects
- CONTRITE: ProjectionRebuildReceipt
- DEFERENTIAL: PreferenceDecisionReceipt

---

## 7) Implementation notes (v0)

1) Start with 5 moods: CALM, CURIOUS, SKEPTICAL, PARANOID, CONTRITE.
2) Encode mood selection as a state machine with guards, not as an LLM choice.
3) Make mood configs versioned artifacts; log mood transitions as events.
4) Ensure all privileged actions depend on mood + policy tokens.

---

## 8) Prompt-ready doctrine block (optional)

MOODS ARE CONFIG, NOT VIBES.
- CALM: execute
- CURIOUS: inquire
- SKEPTICAL: verify
- PARANOID: harden
- BOLD: expand
- CONTRITE: recover
- PETTY: adversarial
- DEFERENTIAL: ask preferences

TRANSITIONS ARE GUARDED BY RECEIPTS AND STATE.
