# The Mind Model: CONJECTURE, E4, and Spiral Development

This document defines a single “mind model” framework for Choir: a small set of epistemic registers and control-loop patterns that make agentic systems legible, verifiable, and compounding under adversarial pressure.

The central idea is not “world models” versus “reward models” versus “language models.” It is the **MIND MODEL**: the active, bounded representation that determines what the system can (a) notice, (b) assert, (c) test, (d) value, and (e) do.

## 0) Core premises

1) The system never acts on “the world.” It acts on a representation plus interfaces.
2) The representation is observer-relative: defined by tools, permissions, evidence, and verifiers.
3) Therefore, *epistemics is control*. If the epistemic layer is sloppy, actions become unsafe and incentives become gameable.
4) Compounding happens by refining the mind model: not by adding prose, but by tightening what can be asserted, tested, bounded, and replayed.

## 1) The E4 register (AHDB / “audible”)

E4 is a compact register for high-tempo control. It is surprisal-first: it stores only deltas that change decisions.

### ASSERT
A claim treated as true **within a declared scope** because it is supported by receipts (evidence bindings and/or verifier outputs).
ASSERT is “weighted observation,” not raw observation.

Required fields:
- CLAIM (scoped)
- EVIDENCE POINTERS (hash+span)
- VERIFIER RESULT (pass/fail + version)
- RECEIPT (run/event references)

### HYPOTHESIZE
A conjecture used to guide action under uncertainty.

Required fields:
- CLAIM (what might be true)
- DISCRIMINATING TEST (what would settle it)
- BUDGET (time/iterations/tokens)
- PROMOTION RULE (what makes it ASSERT)

### DRIVE
A priority ordering or constraint that governs decisions. DRIVE is the “policy shape” the system is optimizing under.

Required fields:
- PRIORITY (what matters most right now)
- TRADE-OFF (what is being sacrificed)
- ANTI-DRIVE (red line: what must not be sacrificed)

### BELIEVE
A statement that bounds the feasible action space: what the system treats as possible, permissible, or likely, given its current observer model.

Required fields:
- PRIOR (the belief)
- CONFIDENCE (or tier)
- UPDATE TRIGGER (what evidence would change it)
- EFFECT (what decisions it changes)

### Surprisal rule
The register must remain small and sharp:
- Do not assert a litany; assert only what would change the next move.
- Do not list obvious drives; list the non-default trade-offs.
- Do not list generic beliefs; list priors that actually change strategy.

## 2) HYPERTHESIS: the blind-spot register

HYPERTHESIS is not a belief; it is the explicit encoding of **what the current observation/verifier regime cannot see**.

It is the “edge of testability” induced by finite tools, finite budgets, and finite verifiers. If left null, the system drifts into overconfidence.

Required fields:
- BLIND SPOT: what cannot currently be tested/observed
- WHY INVISIBLE: which boundary causes this (missing data/tool/permission/cost/semantics/adversary)
- RISK: what goes wrong if this blind spot is exploited
- BOUND: what we can do now (tighten scope, add verifier, add redundancy, quarantine, require approval)

Operational rule:
- No high-impact ASSERT is acceptable unless its implied hypertheses are named and bounded.

## 3) CONJECTURE: the synthesis of HYPOTHESIZE + HYPERTHESIS

A CONJECTURE is the operational synthesis that refines the mind model.

Instead of “a bigger claim,” CONJECTURE is an epistemic object that packages:
- the claim at risk (hypothesis),
- its blind spot boundary (hyperthesis),
- and the smallest observer change that reduces the blind spot.

### Definition
CONJECTURE = (CLAIM, TEST, EDGE, ΔO, SCOPE)

Where:
- CLAIM is the proposition under consideration.
- TEST is the discriminating check under the current observer model.
- EDGE is how CLAIM could be wrong without detection.
- ΔO is the smallest observer upgrade that reduces EDGE (new verifier, new data, new sandbox constraint, new adversarial check).
- SCOPE is the domain in which ASSERT is permitted if TEST passes.

### Why CONJECTURE is a refinement of the mind model
Even if CLAIM fails, the system learns:
- what the boundary was,
- how to shrink it,
- and how to prevent similar over-assertion in the future.

CONJECTURE is therefore the unit of compounding: it produces new verifiers, new receipts, and tighter scopes.

## 4) Spiral development as rotational passes

“Phase” here means rotation, not a stage. Each pass changes direction around an invariant axis (objective/risk), producing new information that changes the next pass.

A canonical mode machine:
- INQUIRE → BUILD → VERIFY → HARDEN → EXPAND (repeat)

### INQUIRE
Purpose: collect transformative information and update AHDB + hypertheses.
Outputs:
- 30-second demo definition
- top hypertheses (named, bounded)
- next two passes only (detailed), parking lot beyond

### BUILD
Purpose: smallest end-to-end walking skeleton.
Outputs:
- runnable demo
- minimal receipts

### VERIFY
Purpose: convert key hypotheses into assertions via tests/verifiers.
Outputs:
- passing verifiers
- replay determinism checks

### HARDEN
Purpose: reduce hyperthesis risk via isolation, policy gates, adversarial checks.
Outputs:
- tightened capabilities
- anomaly detectors
- negative tests (anti-regressions)

### EXPAND
Purpose: broaden scope only when prior passes are green.
Outputs:
- more coverage, edge cases, performance, integration breadth

### Spiral invariants
- Every pass must produce a verifiable artifact.
- Every pass must reduce or bound at least one top hyperthesis.
- If progress stalls, split until the subproblem is satisfiable.

## 5) Question-asking policy (token-optimal inquiry)

Ask questions only when they are **transformative**: answering them would materially change:
- ASSERT vs HYPOTHESIZE status,
- the next pass selection,
- policy gates (permissions/quarantine/publish),
- the demo definition,
- risk tier or blast radius,
- DRIVE priorities.

A universal high-value question:
“What would you consider a simple successful demo you could verify in 30 seconds?”

Prefer research and tests over interrogating the user, except for genuine preference or policy decisions.

## 6) Minimal enforcement: linters and gates

If you want these concepts to shape behavior, enforce them mechanically.

Plan lints:
- Reject plans without a 30-second demo and pass-mode rotation.
- Reject plans that fully specify more than 2 passes.
- Reject calendar timelines.

Execution gates:
- Anti-stub gate (no TODO/NotImplemented/mock returns in touched files).
- No new interface without an integration test crossing it.
- Diff budget caps per pass.
- Receipt required for any promoted artifact.

Epistemic gates:
- No ASSERT without receipts/evidence pointers.
- No HYPOTHESIZE without a discriminating test and budget.
- No DRIVE without anti-drive.
- No privileged transition (publish/reward/sign) without hyperthesis bounds.

## 7) Applying spiral development to documentation itself

Documentation is a system. It can be built in rotational passes, with verifiable results.

The mistake is to “write the whole manual.” The spiral approach is:

### Pass 1 (BUILD): Walking skeleton doc
Goal: make the minimum doc that makes the system usable.
Verifiable output:
- A single page that defines AHDB + hyperthesis + conjecture + spiral passes
- One worked example end-to-end
- A checklist that a reader can follow to produce a compliant plan

Exit criteria:
- A reader can take a vague task and produce: (demo, two passes, E4 register, hyperthesis list)

### Pass 2 (VERIFY): Consistency and linter alignment
Goal: make the doc internally consistent and enforceable.
Verifiable output:
- A schema appendix (field labels, allowed values)
- A linter checklist that maps each rule to a failure condition
- A glossary of overloaded terms (phase/stage, belief/prior, observation/assertion)

Exit criteria:
- Another agent can parse the doc and produce a deterministic validation checklist.

### Pass 3 (HARDEN): Adversarial doc
Goal: make the doc robust against misinterpretation and gaming.
Verifiable output:
- A “common failure modes” section (what lazy agents do)
- Counterexamples and corrections
- “No Copy as a syscall” policy and excerpt limits
- Security notes: message authority rules (DATA vs ATTESTATION vs DECISION)

Exit criteria:
- If someone tries to misuse the framework (e.g., assert without evidence), the doc makes it hard to justify.

### Pass 4 (EXPAND): Libraries of patterns and templates
Goal: scale adoption without bloating the core.
Verifiable output:
- Pattern library: research audits, coding refactors, fund-signing approval packets
- Template pack: SpiralPlan.v1, AUDIBLE.REGISTER, CONJECTURE objects, receipts
- Examples across domains (coding, research, writing)

Exit criteria:
- Users can pick an archetype and get a ready-made pass plan + verifiers.

### Meta-rule for docs
Keep the core doctrine short and stable; expand via appendices and templates. The core should fit in one sitting and survive compaction.

## 8) One compact doctrine block (prompt-ready)

AUDIBLE.REGISTER (E4)
- ASSERT: only with receipts
- HYPOTHESIZE: only with test + budget
- DRIVE: include anti-drive
- BELIEVE: include update trigger

HYPERTHESIS
- name blind spots; bound them

CONJECTURE
- package (claim, test, edge, ΔO, scope)

SPIRAL PASSES
- INQUIRE → BUILD → VERIFY → HARDEN → EXPAND

RULES
- SURPRISAL-FIRST: store deltas that change decisions
- INVERT ALWAYS: antithesis, alternatives, red lines, blind spots
- NO COPY: cite by pointer; minimal snippets only
- NO PRIVILEGE WITHOUT RECEIPTS: publish/reward/sign require attestations

---

This document is itself a Pass 1 “walking skeleton.” It should be tightened by aligning each term to a schema and each rule to a linter failure condition, then hardened with adversarial examples.
