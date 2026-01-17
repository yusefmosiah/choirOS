# Doctrine / Spec / Notes Governance Spec (v0)

This document defines the governance model for Choir documentation and “truth-bearing text.” It formalizes:
- DOCTRINE (rare, human imperatives/invariants),
- SPECS (enforceable, modular interfaces/policies),
- NOTES (high-velocity, exploratory progress artifacts),
and the workflow by which changes are proposed, reviewed, and promoted.

This governance model is designed to:
- keep docs from growing without bound,
- prevent “false docs,”
- preserve high development velocity,
- and ensure changes to invariants require real evidence.

---

## 1) Document tiers

### 1.1 DOCTRINE (stable, human-facing)
Purpose:
- Define imperatives and invariants.
- Establish the “spine” of the system: what must always be true.

Properties:
- Small.
- Rarely changed.
- Changes require stronger evidence and a higher bar.

Examples:
- “WE ASSERT. NO ASSUME.”
- “ASSERT cites only PROMOTED atoms.”
- “NO COPY is a syscall.”
- “MOODS are configs; transitions are guarded by receipts.”
- “Local plane never propagates to global without explicit PUBLISH.”

### 1.2 SPECS (enforceable, modular)
Purpose:
- Define interfaces, schemas, policies, lifecycles, and operational rules.
- Serve as inputs to linters/verifiers and platform configuration.

Properties:
- Versioned, modular, composable.
- Changed deliberately, but more frequently than doctrine.
- Each spec change should be traceable to a contradiction, bug, or new surface area.

Examples:
- CHOIR_MOODS_SPEC.md
- TWP_SPEC.md
- CHIPS_TOPIC_ATTESTATION_SPEC.md
- CHOIR_LOCAL_VC_GLOBAL_BOUNDARY_SPEC.md

### 1.3 NOTES (progress artifacts)
Purpose:
- Capture learnings, experiments, partial plans, and “what we tried.”
- Enable continuity without requiring correctness.

Properties:
- Allowed to be wrong.
- High velocity.
- Must be clearly marked as non-canonical.
- Can be promoted into specs; rarely into doctrine.

Examples:
- experiment notes
- bug diaries
- design sketches
- run postmortems
- “hyperthesis disclosures” before they’re formalized

---

## 2) Lifecycle states for docs

Each doc must declare:

STATUS: DRAFT | ACTIVE | STALE | ARCHIVE

Definitions:
- DRAFT: exploratory, not yet binding.
- ACTIVE: canonical; must not be false.
- STALE: known drift; requires revision or demotion.
- ARCHIVE: kept for provenance; not part of working set.

Rules:
- DOCTRINE docs are almost always ACTIVE; STALE is a crisis state.
- SPECS can go STALE during transitions, but must have a remediation plan.
- NOTES are typically DRAFT and can be archived freely.

---

## 3) Roles and authority overlay

This spec uses the director/associate overlay as an authority model atop the “AI computer state machine.”

### 3.1 ASSOCIATE (runner)
May:
- execute RUNs under a MOOD configuration,
- write NOTES freely,
- emit SPEC_CHANGE_REQUEST objects,
- propose spec deltas (as patches), but cannot merge to ACTIVE specs/doctrine.

May not:
- directly modify DOCTRINE,
- directly modify ACTIVE SPECS without approval,
- mark docs ACTIVE/STALE/ARCHIVE.

### 3.2 DIRECTOR (governor / scheduler)
May:
- accept/reject SPEC_CHANGE_REQUESTs,
- merge changes into SPECS,
- mark specs STALE/ACTIVE/ARCHIVE,
- approve doctrine changes (rare; with heightened procedure),
- enforce doc budgets and consolidation.

Must:
- require evidence and receipts for spec/doctrine changes,
- prefer merging into existing docs over creating new ACTIVE docs,
- keep doctrine small.

### 3.3 REFEREE (verifier/policy engine)
May:
- produce attestations and deterministic policy decisions,
- fail builds/linters when specs/doctrine are violated.

May not:
- edit docs directly (it’s an oracle, not an author).

---

## 4) Change request objects (typed)

All nontrivial changes to SPECS/DOCTRINE must be proposed via a typed request.

### 4.1 SPEC_CHANGE_REQUEST (SCR)
Fields:
- ID: content-addressed hash or run-linked ID
- TARGET: doc/module identifier
- TYPE: BUGFIX | CLARIFICATION | NEW_SURFACE | DEPRECATION | CONSOLIDATION
- CLAIM: what is wrong / missing
- EVIDENCE: receipts, failing verifier output, contradiction proof
- PROPOSED_DELTA: minimal diff (or structured summary)
- RISK: what breaks if we change it
- COMPAT: migration / backward compatibility plan (if needed)
- REQUESTOR: run id / associate id

Acceptance criteria (director):
- Evidence exists and is specific.
- Delta is minimal and modular.
- If NEW_SURFACE, it does not duplicate existing doctrine/spec.
- If CONSOLIDATION, it reduces doc sprawl.

### 4.2 DOCTRINE_CHANGE_REQUEST (DCR)
Same as SCR plus:
- INVARIANT: the invariant being changed
- WHY NOW: why doctrine must change rather than a spec/implementation tweak
- ALTERNATIVES: ways to avoid doctrine change
- BLAST RADIUS: what systems or user mental models change
- REQUIRED APPROVALS: human signoff threshold (if applicable)

Doctrine change bar is high.

---

## 5) Promotion workflow: NOTES → SPECS → DOCTRINE

### 5.1 Notes capture (low friction)
Associates write notes as needed. Notes must include:
- link to the run/receipt that generated them
- whether they are exploratory or corrective
- any conjectures/hypertheses discovered

### 5.2 Promotion to SPEC (deliberate)
To promote a note into a spec:
- extract the invariant or interface that must become enforceable
- write a minimal delta to an existing spec module
- add/adjust a linter/verifier rule (if applicable)
- mark old notes ARCHIVE or keep as provenance

### 5.3 Rare promotion to DOCTRINE (ceremonial)
Only do this when:
- the invariant must be user-visible and stable
- the concept is load-bearing across the system
- it has survived enough iteration to be “spine-worthy”

---

## 6) Doc budget and sprawl control

### 6.1 Budget rule
Per feature / run:
- NOTES can grow freely.
- SPEC deltas should prefer modifying existing modules.
- New ACTIVE spec docs require explicit justification and an “ownership” header.

### 6.2 Consolidation rule
If a feature creates more than one new note/spec fragment:
- the director must schedule a CONSOLIDATION pass within N cycles:
  - merge overlapping docs,
  - archive redundant docs,
  - update the index.

### 6.3 Index rule
A single index (docs/00_INDEX.md) is the only entry point. Every ACTIVE doctrine/spec doc must be reachable from it.

---

## 7) Doc truthfulness: “docs must not be false”

Interpretation:
- DOCTRINE and ACTIVE SPECS must match reality.
- NOTES may be wrong but must be labeled.

Enforcement:
- Spec lints: broken links, missing headers, stale flags older than N days.
- Doc-tests (where feasible): check claimed moods/syscalls/policies exist in config.
- If drift is detected: mark doc STALE and file SCR to repair.

---

## 8) Operational policy: docs updates are low-stress

Docs can be pushed to main with low friction because:
- they don’t change runtime behavior directly unless wired into verifiers/policy,
- and their lifecycle is explicit (ACTIVE vs DRAFT vs STALE).

However:
- ACTIVE docs must pass doc-lints.
- Spec changes that affect runtime must include compat/migration notes.

---

## 9) “Land the plane” for doc work (optional hygiene)

Even in a crash-safe system, periodic doc hygiene is valuable.
A DOC_HYGIENE run:
- finds STALE docs and files SCRs
- merges redundant notes
- updates the index
- ensures doctrine remains small

This is the “refuel midair” version of landing: keep the spine coherent without requiring big end-of-session reports.

---

## 10) Prompt-ready doctrine block (optional)

DOCTRINE = IMPERATIVES + INVARIANTS (RARE CHANGE)
SPECS = ENFORCEABLE INTERFACES + POLICIES (DELIBERATE CHANGE)
NOTES = PROGRESS ARTIFACTS (FREE CHANGE)

ASSOCIATE:
- WRITE NOTES
- FILE SPEC_CHANGE_REQUEST

DIRECTOR:
- APPROVE/MERGE SPEC CHANGES
- RARELY CHANGE DOCTRINE
- ENFORCE DOC BUDGETS

REFEREE:
- ATTEST + FAIL LINTS

## 11) Backlinks and revisions (zettelkasten rule)

- Docs must not manually maintain backlink lists.
- All backlinks are computed as projections from content-addressed REFERS_TO/DEPENDS_ON/REVISES edges.
- Revisions are explicit: new doc version + REVISES edge; old versions remain for provenance.
