# Zettelkasten Substrate Spec (v0): Content Addressing, Versioning, Backlinks

This document updates Choir’s documentation substrate to match current thinking: every meaningful artifact is a **content-addressed card**; revisions are **new objects with explicit edges**; backlinks are **computed projections**, not manually maintained lists.

This is “zettelkasten” as an OS substrate: compounding knowledge without wiki drift.

---

## 1) Core primitives

### 1.1 Object (card)
An OBJECT is immutable and content-addressed.

- object_id = hash(canonical_bytes)
- type: DOCTRINE | SPEC | NOTE | HYPERTHESIS | CONJECTURE | EVIDENCE_CARD | ATTESTATION | RECEIPT | …
- schema_version
- body (typed fields; prose only in bounded fields like `markdown`)
- references: [object_id] (outbound links only; no backlinks stored)

Rule:
- no in-place edits; “edit” means creating a new object.

### 1.2 Edge (link)
Edges are first-class records (also content-addressed) that relate objects.

Minimum edge types:
- REFERS_TO(A, B)
- DERIVED_FROM(A, B)
- EVIDENCE_FOR(binding_or_claim, evidence_card_or_extract)
- CONTRADICTS(binding_or_claim, evidence_card_or_extract)
- DEPENDS_ON(spec_or_doctrine, spec_or_doctrine)
- REVISES(new, old)
- SUPERSEDES(new, old)
- RETRACTS(retraction, target)

Edges are appended as events (or stored in an edge table), never embedded as mutable lists.

### 1.3 Backlinks (projection)
Backlinks are **computed** as a projection over edges:

BACKLINKS(B) = { A | edge(A → B) exists }

No manual backlink editing. No stale backlink lists.

---

## 2) Versioning and “truth-bearing text”

### 2.1 Revisions
Revisions are explicit:

- REVISES(new_doc, old_doc)
- (optional) SUPERSEDES for stronger replacement semantics
- (optional) RETRACTS for invalidation semantics

### 2.2 Tier constraints
- DOCTRINE (ACTIVE) must not be false; changes are rare and ceremonially justified.
- SPECS (ACTIVE) must not be false; changes are deliberate and linter-backed.
- NOTES (DRAFT) may be wrong; they are telemetry/progress and must be promotable.

A NOTE becomes a SPEC only via explicit promotion workflow (see governance spec).

---

## 3) Storage model (local-first)

### 3.1 Notes are events, not repo files
Notes are stored as evented objects outside git by default:
- prevents repo pollution and accidental leakage
- allows crash-safe restart and replay
- makes “failed runs leave no code” compatible with continuity

### 3.2 Docs and code in git (canonical, minimal)
Git stores:
- verified code
- ACTIVE DOCTRINE/SPECS (as files)
- verifier/policy configurations (machine-enforced)
- optionally: pointers (object IDs) to the broader object store

The object store (content-addressed cards) is the primary substrate for rich linking and replay.

---

## 4) Retrieval strategy (two-level index)

### 4.1 Deterministic graph queries (exact)
- outbound links and computed backlinks for exact navigation
- dependency graphs for specs and doctrines
- provenance graphs for claims/evidence

### 4.2 Vector search (fuzzy, situation-aligned)
Embed typed objects—not raw content dumps.

Recommended embedding targets:
- AHDB deltas
- HYPERTHESIS
- CONJECTURES
- EVIDENCE_CARD metadata
- SPEC/DOCTRINE titles + bounded summaries

Avoid embedding large raw payloads as a primary index. Raw payloads remain available by handle.

---

## 5) UI implications (web desktop)

The desktop renders objects as “cards”:
- title + type + status
- outbound links
- computed backlinks
- revision lineage (REVISES chain)
- receipts and provenance handles

Primary interactions:
- VIEW
- REVISE (creates new object + REVISES edge)
- PROMOTE NOTE → SPEC (director-governed)
- ARCHIVE (mark object inactive; history remains)

---

## 6) Enforcement (linters and invariants)

Required checks:
- all referenced object IDs exist
- all ACTIVE doctrine/spec objects are reachable from a single index root (optional but recommended)
- no manual backlink lists in ACTIVE docs (backlinks must be projections)
- docs include STATUS + TYPE + schema_version headers (for ACTIVE tier)

---

## 7) Summary doctrine (prompt-ready)

EVERYTHING IS A HASHED CARD.
- EDITS CREATE NEW OBJECTS.
- REVISES IS AN EDGE.
- BACKLINKS ARE PROJECTIONS.
- NOTES ARE EVENTS; DOCTRINE/SPECS ARE CANON.
