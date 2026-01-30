# Agentic Computer Position Paper
Status: DRAFT
Date: 2026-01-30
Owner: ChoirOS Core

## Thesis
Agentic systems should treat the compute substrate as a governed environment with
explicit capability boundaries, auditable side effects, and replayable state.

## Principles
- Event-sourced truth: immutable logs enable replay and forensic analysis.
- Projection isolation: materialized views are derived, not authoritative.
- Capability gating: tools and network access are explicit and bounded by mode.
- Verifiable outcomes: artifacts and attestations back every critical action.

## Implications for ChoirOS
- NATS is the system-of-truth for events.
- Projections live in libsql and are rebuilt from the log.
- Runtime emits events only; projectors materialize state.
- Verifiers and auditors provide structured accountability.
