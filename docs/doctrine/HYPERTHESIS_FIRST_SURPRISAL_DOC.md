# Hyperthesis-First: A Surprisal-Descending Introduction to Choir

This document is intentionally ordered **surprisal-descending**: it starts with the least-common but most load-bearing ideas, then moves toward increasingly familiar engineering patterns. It is “unusual → expected” by design.

---

## 0) HYPERTHESIS (why we need a word)

A **hypothesis** is a claim that can change given admissible evidence.

A **hyperthesis** names what most systems leave null: the boundary conditions under which a claim cannot be updated—because the observer cannot see, cannot test, or would reinterpret evidence to avoid updating. It is meta-awareness as an object.

Etymology (useful, not pedantic)
- **hypo-** (under) + **thesis** (placing/proposition): a proposition placed under test.
- **hyper-** (over/beyond) + **thesis**: a proposition or posture that stands above the test loop; it is structurally insulated from update.

Hyperthesis is the shadow every testable claim casts: what remains outside the test’s reach, the “unsaid story,” the blind spot, the self-sealing rationalization.

Why it matters
- Most humans and most agent systems operate with **null hyperthesis**: they cannot name what they cannot test.
- Null hyperthesis produces false confidence, drift, and reward hacking.
- Explicit hyperthesis turns ignorance into an agenda: bound it, test it, or quarantine it.

Minimal schema
HYPERTHESIS
- BLIND SPOT: what cannot be tested/observed under the current observer model
- WHY: which boundary causes it (tool limits, permissions, cost, semantics, adversary)
- RISK: what goes wrong if this blind spot is exploited
- BOUND: how to constrain action while it remains open (tighten scope, add verifier, require approval)

Hyperthesis is valuable even when you can’t act immediately. Disclosure is security. But hyperthesis must not authorize privilege.

---

## 1) MIND MODELING (the only model that matters)

People talk about world models, reward models, language models, mental models. In an agentic system, the relevant object is the **mind model**: the bounded representation that determines what can be noticed, asserted, tested, valued, and done.

The mind model is not “the world.” It is the system’s active projection:
- of evidence,
- of constraints,
- of allowable actions,
- and of what counts as an update.

This is why “technology is neutral” is incomplete. The structure of the mind model determines which equilibria are reachable.

---

## 2) Intelligence as knowledge over misconceptions

A simple but operational definition:

**Intelligence = Knowledge / Misconceptions**

Continual learning fails when it only adds to the numerator (more memories, more tokens) but does not reduce the denominator (actively corrected misconceptions).

Inside neural network weights, correcting misconceptions is difficult because representation is distributed: you can’t easily “edit the mistake” without side effects. The alternative is system-level learning:
- make misconceptions explicit,
- make corrections explicit,
- make prevention explicit (regression tests / verifiers),
- and make it all replayable.

This is why Choir emphasizes receipts, promotion rules, and verification loops. The system learns by subtracting misconceptions in state, not by hoping weights silently update.

---

## 3) CONJECTURE (the synthesis that consumes hyperthesis)

A hypothesis without hyperthesis is brittle.
A hyperthesis without a plan is paralyzing.

A **conjecture** is the synthesis object that refines the mind model:

CONJECTURE = (CLAIM, TEST, EDGE, ΔO, SCOPE)

- CLAIM: what might be true
- TEST: how we would know (under current observer)
- EDGE: how it could be wrong without detection (the hyperthesis boundary)
- ΔO: minimal observer upgrade that reduces EDGE (new verifier, new data, new isolation)
- SCOPE: where the claim is assertable if TEST passes

Conjecture is the unit of compounding because it converts blind spots into discriminating tests and bounded action.

---

## 4) AHDB (the state vector)

Most “context engineering” focuses on stuffing documents into context. Choir treats cognition as a **state vector** that is small, typed, and updateable:

ASSERT
- what is true enough to act on (with receipts)

HYPOTHESIZE
- what might be true (with discriminating tests and budgets)

DRIVE
- what we optimize now (with explicit anti-drive / red line)

BELIEVE
- what actions are feasible/allowed/likely (with update triggers)

AHDB is surprisal-first. It stores only deltas that would change the next action if different.

AHDB is not a chat history. It is the control register of the machine.

---

## 5) Spiral development (rotation, not stages)

“Phase” usually means “stage.” Choir uses phase as **rotation**: change heading to reduce uncertainty while keeping an invariant axis (objective/risk).

A canonical rotation:
INQUIRE → BUILD → VERIFY → HARDEN → EXPAND

- INQUIRE: reduce ambiguity, form conjectures
- BUILD: smallest end-to-end slice
- VERIFY: convert hypotheses into assertions via tests
- HARDEN: bound hypertheses with security gates and negative tests
- EXPAND: widen scope only after green signals

The point is not tiny work. The point is sustained flow with real feedback.

---

## 6) The Automatic Computer pattern (the big synthesis)

Beyond “a model in a loop” (tool calling agent), and beyond “Ralph” (session restart loop), the Automatic Computer is:

- a **state machine** with guarded transitions,
- a **small state vector** (AHDB + hyperthesis + conjectures),
- **verifier-in-the-loop** producing attestations,
- **mechanical version control** to keep live updates safe,
- and strict **capability gating** (moods).

The LLM harness is a processor that proposes instructions.
The state machine is the OS that decides what can happen.

---

## 7) Verification green threads (why it must be isolated)

Verification is essential. Raw verification output is token noise.

Therefore verification must be a “green thread”:
- run verifiers in an isolated sub-session
- store raw logs as artifacts
- emit structured attestations only
- update AHDB from attestations, not prose

This makes autonomy trustable and prevents context poisoning.

---

## 8) Local-first safety and version control

A prosumer OS must be safe to hot reload.

Therefore:
- failed runs leave no code
- only verified code enters git
- notes are events (telemetry), not repo artifacts

Mechanical VC is a UX primitive:
CHECKPOINT / DIFF / REVERT / PREVIEW / SAFE APPLY

---

## 9) Social epistemics (later, optional, but coherent)

Runs are per-user. Global ASSERT/PROMOTE/ATTEST are social actions.

Boundary:
- local workspaces never propagate to global without explicit PUBLISH
- promotion is voluntary and collateralized
- attestations are subscribable (topic streams)
- rewards vest based on survival and independent reuse
- “taste-weighted promotion” prevents wallet-size authority

This is how the system becomes a corrective to discourse rather than brainrot.

---

## 10) What Choir is not

- Not a chatbot.
- Not a pile of plugins.
- Not “run 30 agents and pick the best.”
- Not “summarize everything into markdown.”

Choir compiles untrusted reality into asserted state through verifiers, receipts, and guarded transitions.

---

## 11) Canonical one-liners (memes, but true)

WE ASSERT. NO ASSUME.  
NO VERIFIER → NO ASSERT.  
FAILED RUNS LEAVE NO CODE.  
HYPERTHESIS NAMES THE BLIND SPOT.  
CONJECTURE SHRINKS THE EDGE.  
AHDB IS THE STATE VECTOR.  
MOODS ARE CONFIG, NOT VIBES.  
PUBLISH IS EXPLICIT. PROMOTION IS VOLUNTARY.

---

This document is doctrine-adjacent: it should remain short, sharp, and true. Details live in specs.
