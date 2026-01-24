# ChoirOS Master Doc
Status: ACTIVE
Updated: 2026-01-23

## 1) Purpose and scope
This document is the single, coherent entry point to the ChoirOS architecture. It unifies the system view across doctrine, specs, and implementation notes, and it highlights temporality: what is implemented now vs. what is still a designed future state. It is not a replacement for the detailed specs; it is the spine that explains how they connect.

## 2) Documentation tiers (authority and temporality)
ChoirOS uses a tiered document model:
- **Doctrine**: invariant, human-facing rules that are intended to be stable and never false. Changes are rare and require strong evidence.
- **Specs**: enforceable interfaces, schemas, and policies that describe how the system should behave.
- **Notes**: planning, progress logs, and review artifacts; they can be wrong and can be archived without ceremony.
- **Archive**: historical artifacts for provenance and continuity; not part of the active working set.

This tiering is explicitly defined so readers can distinguish hard constraints from working plans.

## 3) System overview (current structure)
ChoirOS is a web desktop backed by a Supervisor control plane, an API utility service, and an optional NATS event bus. The Supervisor orchestrates runs, sandboxes, and verification, while the frontend is the user-facing desktop interface. SQLite stores a local event log; artifacts are stored on disk and referenced by pointer events. NATS JetStream is used when available for event distribution. The system also supports sandbox execution using local subprocesses or Sprites for remote isolation.

## 4) Core runtime loop
The core runtime loop follows a controlled execution model:
1. A work item starts a **run**.
2. The Supervisor selects a **mode/mood** (capability profile) and executes the work in a sandbox.
3. Verification lanes generate structured receipts.
4. The Supervisor gates changes and commits only if receipts pass, preserving transactional safety.
5. Events, receipts, and artifacts update the state vector (AHDB + hyperthesis + conjectures).

This loop makes autonomy measurable and reversible rather than conversational.

## 5) Events and types (the system’s nervous system)
Events are the canonical substrate for observability, replay, and state projection. The event contract defines a single subject format and a normalized event type taxonomy:
- Subject format: `choiros.{user_id}.{source}.{event_type}`.
- Event types: `file.*`, `tool.*`, `mode.*`, `artifact.*`, `note.*`, and `receipt.*`.
- Every event has a standard schema (`id`, `timestamp`, `user_id`, `source`, `event_type`, `payload`).

Receipts and notes are typed events, not free-form logs, which lets the system treat evidence as structured state.

## 6) State vector (AHDB + hyperthesis + conjectures)
The control state is intentionally small and typed:
- **AHDB** captures assertions, hypotheses, drives, and beliefs (surprisal-first).
- **Hyperthesis** tracks bounded blind spots that can’t currently be tested.
- **Conjectures** formalize a claim, test, edge, and scope.

These state objects are the inputs to mode selection and verification gates, not narrative text.

## 7) Modes / moods (capability profiles)
Modes (also called moods in docs and code) are deterministic configuration bundles. Each mode defines:
- tool allowlists
- data scope
- model policy and budget
- verifier policy and required receipts
- output policy and stop rules

Modes are not “multiple agents.” They are safety- and budget-aware configurations for a single runtime.

## 8) Sandboxes and security posture
The system assumes adversarial environments and partitions work into trust zones (ingestion, verification, publishing, governance). It uses multiple sandbox classes, tight capability gating, and receipts for privileged actions. The security model is designed to scale from local development to adversarial conditions by unlocking privileges only after integrity gates are met.

## 9) Apps and UI surface
The frontend is a web desktop with core applications such as Files, Writer, Terminal, and Auth-related flows. The UI is designed to expose runs, events, and artifacts rather than hide them, making verification and rollback visible.

## 10) Temporal map: implemented vs. planned
### Implemented or in active use
- Web desktop UI, Supervisor control plane, API service, and local event log.
- Artifacts stored on disk and referenced in the system.
- Optional NATS JetStream event distribution with subject-based routing.
- Mode/mood definitions and tool gating in the Supervisor.

### Specified or future-facing
- Full social epistemics: publish/promote/attest/assert and global knowledge bases.
- AgentFS as a canonical filesystem substrate.
- Tokenized incentives and advanced governance stages.
- Work queue decoupling and more advanced visualization surfaces.

This separation clarifies which documents describe current behavior vs. target architecture.

## 11) Where to go next
- **Architecture**: `docs/ARCHITECTURE_OVERVIEW.md`
- **Vision & invariants**: `docs/CHOIR_CONTEXT.md` + doctrine
- **Specs**: `docs/specs/` (event contract, moods, storage, work queue, security)
- **Ops**: `docs/ops/`
- **Plans and progress**: `docs/notes/`
- **Historical artifacts**: `docs/archive/`
