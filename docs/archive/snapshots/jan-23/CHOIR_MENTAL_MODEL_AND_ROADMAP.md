# Choir Mental Model and Roadmap (v0)

This document consolidates the current mental model of Choir and a pragmatic sequencing plan. It also captures the “event-driven → continuous compute” scaling thesis so the system remains coherent as it grows.

This is a planning artifact: it should be revised frequently. It is not doctrine.

---

## 1) The shortest coherent mental model of Choir

Choir is an **automatic computer**: a state machine OS for LLM execution.

- The LLM harness is a *processor* that proposes actions.
- The *machine* is the OS: moods (capability profiles), event log, content-addressed object store, verifiers, and transactional version control.
- The **AHDB state vector** is the compact control register passed into every run.
- **Verification** is a first-class lane (green threads): raw output becomes artifacts; only typed attestations update authority.
- **Notes are events**; **code is git**; **failed runs leave no code**.

The product journey:
- v0: a personal automatic computer (1-player).
- Later: publish/promote/attest as social epistemics (credibly neutral), under token economics.

---

## 2) Event-driven background agency → continuous compute

### 2.1 The core scaling thesis
“Continuous compute” is the limit of an event-driven system as event rate increases.

- Many lanes (moods) consume events.
- Each run is bounded, transactional, and emits receipts.
- The KB is updated through promoted objects and projections.
- If events arrive faster than queues drain, the system becomes continuously active.

You do not change architecture; you change the operating point.

### 2.2 Why event-driven first
- Token economics: continuous polling/daemons create token furnaces.
- UX: users adopt “power tools” first; constant background agency comes later.
- Trust: “it ran because an event occurred; here are receipts” beats “it’s always doing something.”

### 2.3 What must scale as frequency increases
As the event rate rises, two pressure points dominate:
- **Contention:** multiple contributors touching shared state.
- **Authority:** what becomes ASSERT-able and when.

The mitigations are already core Choir primitives:
- content addressing (immutable objects)
- promotions/attestations (authority pipeline)
- typed pubsub and leases (safe concurrency)
- verifiers and circuit breakers (backpressure)

### 2.4 Backpressure requirements (non-negotiable)
To avoid Gas Town-style burn:
- queue prioritization (verification/anomaly lanes outrank feature work)
- per-lane budgets and rate limits
- circuit breakers (no-delta throttling; repeated failure signature stop)
- lease caps (NET/EXPORT concurrency limits)
- promotion caps (challenge window throughput limits)

---

## 3) Current priority: make the mental model experiential

The highest priority is not adding features; it is making the system **legible and tunable**.

### 3.1 Legibility primitives
- Visualization of the machine state (mind map + context graph + time slider)
- Receipts everywhere (what happened, why, and with what evidence)
- AHDB deltas over time (small, surprisal-first)

The visualization is not decoration; it is the tuning instrument that lets you refine the OS through experience.

---

## 4) Near-term sequencing (reduce sprawl)

This roadmap reduces 500 parallel projects into a disciplined sequence.

### Phase A — Stabilize the 1-player automatic computer (now)
Goal: safe experimentation with minimal review burden.

Deliverables:
1) **Auth security**
   - secure sessions, scoped permissions, least privilege
2) **Mechanical VC in the web desktop**
   - CHECKPOINT / DIFF / REVERT / PREVIEW / SAFE APPLY
   - worktrees per run; transactional commits; discard-on-failure
3) **AHDB integrated in the prototype**
   - state vector injected into every run
4) **Verifier green threads**
   - raw logs as artifacts; structured attestations only
5) **Visualization v0**
   - context graph + mind map + live updates
   - invariant overlays (risk, leases, unverified diffs)

Success criterion:
- You can run overnight and wake up to a coherent, bounded, verified delta.

### Phase B — Unilateral auditor (text-first) as the wedge
Goal: ship something obviously valuable, not just infrastructure.

Deliverables:
- research-as-verification lane (evidence cards + attestations)
- critique pipeline (claims, evidence, omissions, hypertheses)
- publishable artifacts with provenance
- local KB compounding + retrieval keyed on typed state

Success criterion:
- A text input produces an audit that is useful, citeable, and contestable.

### Phase C — Multimodal expansion (after text wedge works)
Goal: generalize the auditor and the OS.

Order:
- images (evidence cards for screenshots/figures)
- audio input/output (podcast review as verifier lane)
- video (later; expensive and noisy)

Success criterion:
- multimodal evidence is integrated into the same content-addressed, attested pipeline.

### Phase D — Social epistemics and cryptoeconomics (later, deliberate)
Goal: credible neutrality and economic security.

Prerequisites (must be true first):
- local-first safety and no accidental global propagation
- promotion/attestation pipeline works locally
- receipts and replay are reliable
- strong anti-waste budgets and circuit breakers

Then:
- chips (credits) for runs and attestations
- voluntary promotion, challenge windows
- taste-weighted promotion (TWP)
- signing service + secrets service (capability-gated)
- blockchain/RPC data connectors as *generic syscalls*, not bespoke integrations

Success criterion:
- expected value of cheating is negative; contribution is positive; neutrality is legible.

---

## 5) Architecture focus principle: accelerate development

A recurring risk is getting pulled into connector sprawl, tokenomics speculation, or “infinite features.” The governing heuristic:

Prefer building primitives that increase the rate of validated progress:
- visualization and replay
- verifiers and attestation lanes
- transactional VC and safe experimentation
- typed state and capability governance

Defer everything that is “more surface area” without multiplying development velocity.

---

## 6) Developing Choir within Choir (bootstrap target)

The goal is to reach a point where:
- Choir’s own development happens inside Choir
- with multiple concurrent lanes (research/verify/execute)
- and the system produces verified, coherent deltas with minimal human review

Once that bootstrap is achieved, you unlock the mainstream automation you’re aiming for:
- design thinking and research phases become workflows
- verifiers are generated and strengthened as part of the loop
- agents can implement connectors and integrations safely and in parallel

---

## 7) The July 2026 user vision (what this enables)

A user inside Choir can:
- build an agentic video editing studio
- build home automation workflows
- build a virtual family office

Because the platform provides:
- safe sandboxes and capability leases
- event-driven background work with receipts
- verifiers and transactional version control
- visualization and replay
- optional publish/promote/attest economies

---

## 8) Open questions (explicit)

- Tokenomics sequencing vs multimodal sequencing: what maximizes adoption and compounding?
- Best minimal UI automation oracle for web desktop apps (reducing flake)?
- What is the smallest viable “connector” surface that survives vendor zombification?
- How to present AHDB and moods in UI without user fatigue?

These should be handled by conjecture-driven experiments and verifier development, not by one-shot planning.
