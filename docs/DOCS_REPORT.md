# ChoirOS Documentation Report
Status: ACTIVE
Updated: 2026-01-23

## 1) Report goals
This report summarizes the documentation set, explains the organization, and highlights the temporal distinction between what is implemented and what is a future target. It also records the consolidation work: creation of a master doc, archival of dated material, and removal of duplicate files.

## 2) How the docs are organized (and why)
The docs now follow a tiered structure so readers can quickly infer authority and time:
- **Master spine**: a single entry point that narrates the system and points to canonical specs.
- **Doctrine**: invariant rules and governance requirements that should not drift.
- **Specs**: enforceable interfaces and system contracts (events, modes, storage, security).
- **Ops and implementation plans**: delivery mechanics and operational hardening.
- **Notes and reviews**: fast-moving planning and progress logs, explicitly non-canonical.
- **Archive**: dated handoffs, test reports, and snapshots kept only for provenance.

This structure makes it explicit which docs describe current truth vs. historical context or future design intent.

## 3) Canonical entry points (ACTIVE)
- `docs/MASTER_DOC.md`: the single coherent architecture narrative.
- `docs/ARCHITECTURE_OVERVIEW.md`: system component diagram and relationships.
- `docs/CHOIR_CONTEXT.md`: vision, invariants, and product shape.
- `docs/CHANGELOG.md`: shipped capabilities and milestones.
- `docs/DEPLOYMENT_PLAN.md`: host vs sandbox deployment and near-term operational plan.
- `docs/SELF_DEV_BOOTSTRAP.md`: bootstrap concerns and self-development constraints.

## 4) Doctrine (ACTIVE)
- `docs/doctrine/CHOIR_DOCTRINES.md`
- `docs/doctrine/DOCTRINE_GOVERNANCE_SPEC.md`
- `docs/doctrine/HYPERTHESIS_FIRST_SURPRISAL_DOC.md`
- `docs/doctrine/THE_MIND_MODEL.md`
- `docs/doctrine/ZETTELKASTEN_SUBSTRATE_SPEC.md`

These documents define invariants and governance. They should be treated as the most stable layer.

## 5) Specs (ACTIVE, but often future-facing)
`docs/specs/` contains the enforceable contracts for system behavior. These are authoritative even when features are not fully implemented. They include:
- Event contract and event types.
- Mood/mode behavior and policies.
- Storage and rollback models.
- Work queue, verification lanes, visualization, and capability boundaries.
- Security models and headless designs.

## 6) Ops and implementation plans (ACTIVE)
- `docs/ops/`: hardening, research roadmaps, and operations checklists.
- `docs/implementation_plans/`: detailed execution plans for major subsystems.

These are operationally oriented and are allowed to evolve as implementation changes.

## 7) Notes and reviews (NON-CANONICAL)
- `docs/notes/`: planning, progress logs, and next-step checklists.
- `docs/reviews/`: deep review diagnostics and gap analyses.

These are intentionally fast-moving and may become stale; they are not treated as system truth.

## 8) Archive (HISTORICAL)
- `docs/archive/handoffs/`: dated handoff notes.
- `docs/archive/reports/`: test reports and verification logs.
- `docs/archive/reviews/`: historical reviews and reconciliation notes.
- `docs/archive/snapshots/`: dated architecture snapshots and strategy updates.
- `docs/archive/planning/`: planning snapshots.
- `docs/archive/notes/`: deprecated notes (including old frontend notes).

Archival preserves provenance without polluting the active working set.

## 9) External READMEs
- `api/README.md`: API-specific setup and endpoints.
- `choiros/README.md`: frontend template README (likely a candidate for replacement with project-specific content).

## 10) Temporality map (current vs. future)
### Current / implemented
- Web desktop UI, Supervisor orchestration, and API utilities.
- Local event log with optional NATS JetStream distribution.
- Artifact storage and basic app surface (Files, Writer, Terminal).
- Mode/mood definitions and tool gating.

### Future / specified
- AgentFS as canonical filesystem substrate.
- Global knowledge, publish/promote/attest workflows.
- Tokenized incentives and governance stages.
- Full visualization graph and non-blocking work queues.

## 11) Consolidation actions taken
- Created a master doc to unify architecture across doctrine/specs/notes.
- Archived dated handoffs, test reports, and older snapshots.
- Removed duplicate doctrine files that were exact copies.

If new docs are added, they should declare their tier and status up front so the temporal and authority boundaries remain clear.
