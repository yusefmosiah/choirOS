# Choir Full System (Design v0): Web Desktop + Sandboxed Associate + Director VC UI + Social Epistemics

This document specifies the full Choir system: a web desktop that runs hot-reloading sandboxed code in an associate, provides a director-controlled version control UI, and supports personal + global knowledge bases with explicit publish/promote/attest/assert semantics.

## 0. Goals and non-goals

Goals
- “Automatic computer” UX: files appear, apps hot-reload, background runs execute.
- Strong safety: local changes are transactional; failures leave no code; kill switches exist.
- Clear boundary between private runs and social/global epistemics.
- Social layer builds on voluntary publication and collateralized promotion (TWP).
- Token economy (chips) funds runs and attestations; rewards vest based on survival and reuse.

Non-goals (v0)
- Full decentralized governance; complex legal/compliance.
- Arbitrary money-moving / signing (future stage).
- Perfect privacy on day one (can be tiered later).

## 1. Three layers (must be kept separate)

### 1.1 Local Workspace VC (safety substrate)
- Checkpoints, diffs, revert, preview branches/worktrees.
- Runs do not directly mutate “main” workspace without verification gates.

### 1.2 Local Epistemics (mind model)
- AHDB state vector + hyperthesis + conjectures.
- Local object lifecycle: UNTRUSTED → QUARANTINED → PROMOTED (local) → RETRACTED (local).
- Local assertions cite only promoted local atoms.

### 1.3 Global Epistemics (social layer)
- Explicit PUBLISH from local → public artifacts.
- Global promotion/attestation/challenge with TWP + chips.
- Global ASSERT cites only PROMOTED global atoms.

(See CHOIR_LOCAL_VC_GLOBAL_BOUNDARY_SPEC.md.)

## 2. System architecture

### 2.1 Web Desktop UI
Primary UI primitives
- Desktop file tree and app tiles.
- Hot reload viewer (iframe/webview) for sandboxed app runtime.
- Checkpoint timeline (mechanical VC).
- “Run console” showing: mood, work item, verifier status, receipts.
- Publish/Promote/Attest panels (social actions, explicit).

### 2.2 Associate Sandbox (hot reload worker)
Runs user app code with hot reload.
- Strict filesystem scope: only project workspace.
- Network off by default (except allowlisted dev needs).
- No platform credentials exposed.
- Emits runtime logs as artifacts; emits receipts.

### 2.3 Director Sandbox (control plane + VC UI)
- Owns the checkpoint timeline and merge/discard operations.
- Evaluates verifier attestations before allowing code to land.
- Selects moods, budgets, verifier plans, and escalations.
- Produces “approval packets” for high-risk actions (publish/export later).

### 2.4 Event Bus (AHDB-typed)
- Pubsub carries typed state proposals and attestations; no freeform agent chat.
- Messages compile into AHDB projections; authority only via attestations and policy tokens.
- Topics: /run/*, /topic/*, /system/*

### 2.5 Storage
- Per-user event log and object store (private).
- Per-user local KB index (embeds AHDB/conjecture/hyperthesis objects).
- Global public object store + global event log + global KB index.

## 3. Execution model (private plane)

A user action triggers:
- create RUN (one work item)
- director selects mood
- associate executes in isolated worktree/sandbox
- verifier green thread runs checks
- director approves commit or discards
- state vector updates (AHDB)

Notes are events; code is transactional.

## 4. Mechanical version control UX (director sandbox)

Minimum primitives
- CHECKPOINT: snapshot (auto before/after verified changes; user can manual).
- DIFF: view patch; highlight verifier outcomes.
- REVERT: undo to checkpoint (atomic).
- PREVIEW: run in separate branch/worktree; merge/discard.
- SAFE APPLY: stage → verify → commit → checkpoint.

Rule: “live reload” is safe because mainline only advances on verified commits.

## 5. Moods (capability profiles)

Moods are deterministic configs that set:
- tool allowlists
- data scope
- model tier
- verifier strictness
- budgets and stop rules

The web desktop surfaces the current mood as a user-legible indicator.
(See CHOIR_MOODS_SPEC.md.)

## 6. Verification in the loop (green threads)

Verifier outputs are stored as artifacts; only structured reports/attestations enter control state.
- Cheap verifier model is sufficient for summarizing test output.
- Director consumes attestations to gate commits and promotion eligibility.

(See VERIFICATION_GREEN_THREADS_SPEC.md.)

## 7. Social epistemics: publish → promote → attest → assert

### 7.1 Publish (explicit export)
User selects a local object or artifact to publish.
- Can publish full artifact or redacted projection.
- Publishing does not grant global authority; it creates a public candidate.

### 7.2 Promote (voluntary collateralized)
Any actor can stake to promote specific atoms (bindings/conjectures/hypertheses).
- Opens challenge window.
- Promotion buys scrutiny, not rank.

### 7.3 Attest (subscribable topic streams)
Attesters subscribe to topic categories and spend chips to produce attestations.
- Delayed rewards based on survival and independent reuse.
- Attester calibration matters.

### 7.4 Assert (global)
Global ASSERT may cite only PROMOTED atoms.

(See TWP_SPEC.md and CHIPS_TOPIC_ATTESTATION_SPEC.md.)

## 8. Chips (credits) and token economy (v0)

Chips pay for:
- RUN execution (unilateral audits, coding loops)
- verification green threads
- attestations on public objects

Chips are bootstrapped via grants to early users. Waste is bounded by budgets and circuit breakers.

## 9. Trust zones and exfiltration defense

Hard rule: do not co-locate private data + network + credentials.

Operationalization
- Research runs in CURIOUS mood in a separate sandbox.
- Execution runs with network off by default.
- Export/publish is a privileged syscall under DEFERENTIAL mood with approvals.

All network egress is via policy tool; no raw curl.

## 10. Docs governance in the product

Docs are first-class and tiered:
- DOCTRINE (rare)
- SPECS (deliberate)
- NOTES (free)

Associates can emit notes and SPEC_CHANGE_REQUESTs; director merges with evidence.
Docs are viewable and editable in the desktop UI; diffs are tracked.

(See DOCTRINE_SPEC_NOTES_GOVERNANCE_SPEC.md.)

## 11. Deployment and separation of repos

- Platform repo: Choir OS + UI + services; CI/CD.
- User workspaces: per-user; never propagate to platform by accident.
- Global KB store: separate service; only touched by explicit publish/promote/attest actions.

## 12. Bootstrapping sequence (spiral)

Spiral 1: 1-player headless + local VC timeline  
Spiral 2: web desktop UI + hot reload sandbox + checkpoints  
Spiral 3: verifier green threads + director commit gate  
Spiral 4: publish (local→public) without economics  
Spiral 5: global promotion/attestation with conservative chips and delayed rewards  
Spiral 6: TWP calibration and anti-collusion + topic streams
