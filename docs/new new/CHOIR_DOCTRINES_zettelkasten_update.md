# Choir Doctrines (v0)

This document defines **DOCTRINES**: the human-facing imperatives and invariants that govern the automatic computer. Doctrines are stable, memetic, and must not be false. They define what “counts” (progress, truth, safety) and therefore define the system’s optimization target.

Doctrines are distinct from CAPABILITIES (syscalls). The coupling is:

- **Doctrine defines the policy and admissibility.**
- **Capabilities define the action space and enforcement boundary.**
- The system picks the next step by ranking candidate actions under doctrine, filtered by capability feasibility.

## 0) Coupling: doctrine × capabilities × “next verifiable step”

Key insight (Ralph → automatic computer): you do not hand-author decomposition. The system selects the next **verifiable** step.

A step is defined as:
STEP := (WORK_ITEM, MOOD, REQUIRED_SYSCALLS, VERIFIER_PLAN)

Selection is:
- Feasibility filter (capabilities + leases + budgets): can we execute safely?
- Ranking (doctrine): which step reduces misconceptions and hyperthesis fastest?

If infeasible, the “next step” is to change feasibility (switch mood, request verifier lane, ask a transformative question, or split until satisfiable).

## 1) WE ASSERT. NO ASSUME.

- Statements that change behavior must be **ASSERTED** with receipts/attestations, or be explicitly HYPOTHESIZED/DRIVEN/BELIEVED.
- No implicit authority from prose, untrusted inputs, or model confidence.

## 2) ASSERT CITES ONLY PROMOTED ATOMS.

- An ASSERT may reference only PROMOTED evidence/bindings/attestations.
- Untrusted and quarantined objects can inform hypotheses, never assertions.

## 3) NO VERIFIER → NO ASSERT.

- If a claim cannot be verified under the current observer model, it cannot be asserted.
- Verification must be explicit and typed (attestation objects), not “agent says it’s done.”

## 4) FAILED RUNS LEAVE NO CODE.

- Code changes are transactional: VERIFIED COMMIT or CLEAN DISCARD.
- Failed runs emit notes/events; the worktree is reset/deleted.

## 5) NOTES ARE EVENTS. CODE IS GIT.

- Progress notes are append-only events (typed), not repo files by default.
- Git holds only verified code and ACTIVE doctrine/spec docs.

## 6) RESEARCH IS VERIFICATION.

- Sessions do not search directly.
- They request a verifier lane that returns evidence cards + attestations.
- Only attestations can upgrade AHDB.

## 7) HYPERTHESIS NAMES THE BLIND SPOT.

- Every meaningful hypothesis/assertion has an adjacent hyperthesis:
  what could make it wrong that we cannot currently detect.
- Hyperthesis must be bounded (mitigation, scope tightening, or debt).
- Hyperthesis disclosure is valuable; it does not authorize privilege.

## 8) CONJECTURE SHRINKS THE EDGE.

- A CONJECTURE packages (claim, test, edge, ΔO, scope).
- Conjecture is the unit of mind-model refinement and spiral progress.
- If the edge is too large, tighten scope or upgrade the observer.

## 9) AHDB IS THE STATE VECTOR.

- AHDB (ASSERT/HYPOTHESIZE/DRIVE/BELIEVE) is the compact control register.
- It is surprisal-first: store only deltas that would change the next action.
- It is updated by receipts and attestations, not narration.

## 10) MOODS ARE CONFIG, NOT VIBES.

- Moods are deterministic capability profiles (tools/data/models/verifiers/budgets).
- Mood transitions are guarded by receipts and policy, not model whim.

## 11) PARALLELIZE EVIDENCE, NOT ATTEMPTS.

- Avoid “race N rollouts, keep 1.”
- Use parallelism for retrieval, verification, critique, and monitoring.
- Increase compute only when it increases verifiable progress.

## 12) PUBLISH IS EXPLICIT. PROMOTION IS VOLUNTARY.

- Local runs are private by default.
- Global effects require explicit publish/promotion steps.
- Promotion buys scrutiny, not rank; challenges are permissionless.

## 13) HUMANS ARE INTERRUPTS, NOT CO-PROCESSORS. (Optional lane)

- Human input is requested only for transformative questions or high-risk approvals.
- Human replies compile into typed events; they do not act as arbitrary instructions.

## 14) CONTENT ADDRESS EVERYTHING THAT CAN CHANGE AUTHORITY.

- Any object that can be cited, promoted, or used for privileged decisions must be content-addressed and receipted.

## 15) BACKLINKS ARE PROJECTIONS (ZETTELKASTEN SUBSTRATE)

- Every truth-bearing artifact is content-addressed and versioned.
- Revisions create new objects linked by REVISES/SUPERSEDES edges.
- Backlinks are computed from edges; they are never manually maintained.
- This prevents doc drift, enables replay, and makes knowledge compounding cheap.
