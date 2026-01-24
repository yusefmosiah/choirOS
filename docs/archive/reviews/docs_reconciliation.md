# Docs Reconciliation Review (2026-02-XX)

## Scope

### New docs reviewed ("new choir docs to reconcile")
- AGENTIC_CONSULTING_PATTERNS.md
- CHIPS_TOPIC_ATTESTATION_SPEC (1).md
- CHOIR_CAPABILITIES_SPEC.md
- CHOIR_DOCTRINES.md
- CHOIR_FULL_SYSTEM_DESIGN.md
- CHOIR_HEADLESS_1P_DESIGN.md
- CHOIR_LOCAL_VC_GLOBAL_BOUNDARY_SPEC.md
- CHOIR_MOODS_SPEC.md
- DOCTRINE_SPEC_NOTES_GOVERNANCE_SPEC.md
- HUMAN_INTERRUPT_LANE_SPEC.md
- HYPERTHESIS_FIRST_SURPRISAL_DOC.md
- RESEARCH_AS_VERIFICATION_PATTERN.md
- RUN_OUTPUT_POLICY_SPEC.md
- THE_AUTOMATIC_COMPUTER_SECURITY_MODELS.md
- THE_MIND_MODEL (1).md
- TWP_SPEC (1).md
- VERIFICATION_GREEN_THREADS_SPEC.md

### Existing docs reviewed (core, non-archive)
- docs/ARCHITECTURE.md
- docs/CURRENT_STATE.md
- docs/CONTEXT.md
- docs/ROADMAP.md
- docs/THE_AUTOMATIC_COMPUTER.md
- docs/ralph/OVERVIEW.md
- docs/ralph/CONTRACTS.md
- docs/bootstrap/README.md
- docs/bootstrap/ARCHITECTURE.md
- docs/bootstrap/PHASES.md
- docs/bootstrap/PHASE3_ARCHITECTURE.md
- docs/bootstrap/AGENT_HARNESS.md
- docs/bootstrap/AGENT_TOOLS.md
- docs/bootstrap/AGENT_HANDOFF.md
- docs/bootstrap/DESKTOP.md
- docs/bootstrap/APPS.md
- docs/bootstrap/AUTH.md
- docs/bootstrap/NATS.md
- docs/bootstrap/STORAGE.md
- docs/bootstrap/FIRECRACKER.md
- docs/bootstrap/STACK.md
- docs/bootstrap/DECISIONS.md
- docs/bootstrap/UNKNOWNS.md
- docs/bootstrap/BLOCKNOTE_MIGRATION.md
- docs/commits/2026-01-09-automatic-computer-infrastructure.md
- PLANNING.md
- next_steps_checklist.md
- agent_brief_implementation_recovery.md
- docs_review.md
- THE_MIND_MODEL.md
- choiros/NOTES.md

Notes:
- docs/archive/* not reconciled in this pass (historical narrative; treat as ARCHIVE).
- docs/CHANGELOG.md and choiros/README.md are informational; no conflicts found.

---

## Core alignments (old vs new)

1) Director/Associate dual-sandbox model
- Old: docs/ARCHITECTURE.md, docs/ralph/*, docs/bootstrap/*
- New: CHOIR_FULL_SYSTEM_DESIGN.md, CHOIR_HEADLESS_1P_DESIGN.md, THE_AUTOMATIC_COMPUTER_SECURITY_MODELS.md
- Alignment: consistent on director control plane, associate execution, no secrets in sandboxes, Vite-in-associate.

2) Git checkpoints as v0 time travel
- Old: docs/ARCHITECTURE.md, docs/ROADMAP.md, docs/bootstrap/PHASES.md
- New: RUN_OUTPUT_POLICY_SPEC.md, CHOIR_LOCAL_VC_GLOBAL_BOUNDARY_SPEC.md
- Alignment: transactional code changes, checkpoints/preview/undo, no partial code on failure.

3) Event sourcing / receipts as system truth
- Old: docs/THE_AUTOMATIC_COMPUTER.md, docs/bootstrap/NATS.md, docs/commits/*
- New: RUN_OUTPUT_POLICY_SPEC.md, VERIFICATION_GREEN_THREADS_SPEC.md, CHOIR_MOODS_SPEC.md
- Alignment: both treat events/receipts as authoritative state, with replay as goal.

4) Safety boundaries and trust zones
- Old: docs/ARCHITECTURE.md, docs/bootstrap/FIRECRACKER.md
- New: THE_AUTOMATIC_COMPUTER_SECURITY_MODELS.md, CHOIR_LOCAL_VC_GLOBAL_BOUNDARY_SPEC.md
- Alignment: separate control plane, sandboxing, strict egress, no co-location of secrets + net + untrusted code.

5) ? bar as utility surface (not chat)
- Old: docs/bootstrap/DECISIONS.md, docs/bootstrap/APPS.md
- New: AGENTIC_CONSULTING_PATTERNS.md, CHOIR_DOCTRINES.md
- Alignment: prompt surface is utilitarian; responses land as artifacts/windows, not chat.

---

## Divergences / conflicts to resolve

1) Event log source of truth and transport
- Old: strong NATS/JetStream emphasis (docs/bootstrap/NATS.md, docs/commits/2026-01-09-automatic-computer-infrastructure.md) but also "deferred" in bootstrap docs.
- New: receipts + event log required, transport unspecified; focus on AHDB + attestations.
- Decision needed: Is NATS mandatory in v0, or optional behind an event-store interface? Update docs/ROADMAP.md, docs/ARCHITECTURE.md, docs/ralph/CONTRACTS.md, and specs accordingly.

2) Fanout / wide-agent search vs "parallelize evidence, not attempts"
- Old: DECISIONS.md and UNKNOWNS.md promote wide-agent fanout.
- New: CHOIR_DOCTRINES.md and AGENTIC_CONSULTING_PATTERNS.md discourage full rollout fanout; parallelize verification/retrieval only.
- Decision needed: keep fanout as a specialized PETTY/CURIOUS lane (evidence-only), or reframe it as a verifier policy rather than general execution.

3) Tooling model: 4 tools vs capability syscalls + leases
- Old: docs/bootstrap/AGENT_TOOLS.md defines 4 tools; contracts pass allowed_tools.
- New: CHOIR_CAPABILITIES_SPEC.md defines syscall classes, leases, receipts.
- Decision needed: map tools to capability classes and update director/associate contract fields (allowed_tools -> capability leases; verify_profile -> verifier plan).

4) Research execution model
- Old: ? bar can trigger direct retrieval/parse; NATS later.
- New: RESEARCH_AS_VERIFICATION_PATTERN.md forbids direct search in execution sessions; requires verifier lane.
- Decision needed: place parsing/retrieval behind verifier lane in CALM/CURIOUS; update docs/bootstrap/APPS.md and api docs to match.

5) Notes and docs location
- Old: docs, notes, and plans live in repo (PLANNING.md, choiros/NOTES.md, docs_review.md).
- New: RUN_OUTPUT_POLICY_SPEC.md says notes are events, not repo files; DOCTRINE_SPEC_NOTES_GOVERNANCE_SPEC.md introduces doc tiers.
- Decision needed: which existing notes remain in repo (as NOTES/ARCHIVE) vs migrate to event log; establish doc status headers.

6) Economics vocabulary
- Old: CHIPs/USDC in docs/CONTEXT.md; "Thought Bank" framing.
- New: CHIPS (credits) + TWP (promotion) + attestation market; no USDC in v0 docs.
- Decision needed: unify naming (CHIP vs CHIPS), decide if USDC is a separate later-stage spec or remove from core docs.

7) Timeline and scope of event sourcing
- Old: event bus deferred until after Sprites; git-based time travel now.
- New: receipts and verifier attestations required from the start.
- Decision needed: what minimal receipt/event infrastructure is non-negotiable in v0, even if NATS is deferred.

8) Doc governance (index + status)
- Old: no doc status headers or index; bootstrap docs sprawl.
- New: DOCTRINE_SPEC_NOTES_GOVERNANCE_SPEC.md requires status headers and a single index.
- Decision needed: establish doc statuses and a docs index; consolidate or archive redundant docs.

---

## Gaps (new concepts not reflected in old docs)

- AHDB/HYPERTHESIS/CONJECTURE state vector (THE_MIND_MODEL.md) missing from architecture docs and contracts.
- Moods state machine (CHOIR_MOODS_SPEC.md) not integrated into director/associate contracts or tool gating.
- Capability leases and receipts (CHOIR_CAPABILITIES_SPEC.md) not represented in AGENT_TOOLS.md or contracts.
- Verification green threads and attestations (VERIFICATION_GREEN_THREADS_SPEC.md) absent from bootstrap specs.
- Local vs global boundary and publish/promote/attest lifecycle (CHOIR_LOCAL_VC_GLOBAL_BOUNDARY_SPEC.md) missing from older economics docs.
- Doc governance lifecycle (DOCTRINE_SPEC_NOTES_GOVERNANCE_SPEC.md) not applied to current repo docs.

---

## Consolidation plan (docs-only)

### 1) Canonicalize filenames and locations
- Move new docs from `new choir docs to reconcile/` into `docs/` under a consistent layout.
- Rename to remove "(1)" suffixes:
  - CHIPS_TOPIC_ATTESTATION_SPEC.md
  - TWP_SPEC.md
  - THE_MIND_MODEL.md (already present at repo root; keep root or move to docs and update links)

### 2) Apply doc tiers and status headers
Proposed initial mapping (subject to review):

DOCTRINE (ACTIVE)
- CHOIR_DOCTRINES.md
- THE_MIND_MODEL.md (or HYPERTHESIS_FIRST_SURPRISAL_DOC.md as short doctrine intro)

SPECS (ACTIVE or DRAFT)
- CHOIR_MOODS_SPEC.md (ACTIVE)
- CHOIR_CAPABILITIES_SPEC.md (DRAFT)
- VERIFICATION_GREEN_THREADS_SPEC.md (ACTIVE)
- RUN_OUTPUT_POLICY_SPEC.md (ACTIVE)
- CHOIR_HEADLESS_1P_DESIGN.md (DRAFT)
- CHOIR_FULL_SYSTEM_DESIGN.md (DRAFT)
- CHOIR_LOCAL_VC_GLOBAL_BOUNDARY_SPEC.md (ACTIVE)
- THE_AUTOMATIC_COMPUTER_SECURITY_MODELS.md (ACTIVE)
- HUMAN_INTERRUPT_LANE_SPEC.md (DRAFT, non-v0)
- TWP_SPEC.md (DRAFT, non-v0)
- CHIPS_TOPIC_ATTESTATION_SPEC.md (DRAFT, non-v0)

NOTES (ACTIVE or ARCHIVE)
- AGENTIC_CONSULTING_PATTERNS.md
- RESEARCH_AS_VERIFICATION_PATTERN.md (pattern note unless promoted to spec)
- docs/bootstrap/* (likely NOTES; mark STALE where superseded)
- PLANNING.md, next_steps_checklist.md, agent_brief_implementation_recovery.md, docs_review.md, choiros/NOTES.md

### 3) Create a single docs index
- Add `docs/00_INDEX.md` listing ACTIVE doctrine/specs/notes with status and ownership.

### 4) Update existing architecture docs to reference new doctrine/specs
- docs/ARCHITECTURE.md and docs/ralph/CONTRACTS.md should reference:
  - moods (CHOIR_MOODS_SPEC.md)
  - capability leases (CHOIR_CAPABILITIES_SPEC.md)
  - verification lane (VERIFICATION_GREEN_THREADS_SPEC.md)
  - run output policy (RUN_OUTPUT_POLICY_SPEC.md)

---

## Open questions (docs-only)

1) Event log transport: NATS mandatory or optional in v0? If optional, what is the authoritative event store in v0 (SQLite only)?
2) Fanout policy: is wide-agent search deprecated, or constrained to evidence/verification lanes only?
3) Doc tiering: should THE_AUTOMATIC_COMPUTER.md and CONTEXT.md be doctrine, or kept as narrative NOTES?
4) What is the canonical location for THE_MIND_MODEL.md (repo root vs docs/)?
5) Do we standardize on CHIPS (credits) only, or keep USDC/CHIP terms from CONTEXT.md as future-stage economics?
6) How do we integrate the verifier lane with current ? bar parsing flow (api) without breaking v0 UX?

---

## Immediate next steps (docs-only)

1) Decide event log transport and update docs/ARCHITECTURE.md + docs/ROADMAP.md + docs/ralph/CONTRACTS.md.
2) Resolve fanout policy and update docs/bootstrap/DECISIONS.md + UNKNOWNS.md + CHOIR_DOCTRINES.md.
3) Integrate moods/capabilities/verification into the DirectorTask/AssociateResult contract.
4) Add doc status headers and create docs/00_INDEX.md.
5) Move/rename new docs into docs/ and remove duplicates.

