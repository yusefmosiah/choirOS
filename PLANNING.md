# ChoirOS Planning (v0)
Status: ACTIVE
Updated: 2026-01-18

## Canonical references
- docs/SELF_DEV_BOOTSTRAP.md (bootstrap issues + status)
- docs/test_report-2026-01-17c.md (grand verification report)
- docs/specs/CHOIR_HEADLESS_1P_DESIGN.md (headless plan)
- docs/specs/CHOIR_MOODS_SPEC.md (mood policy + guards)
- docs/specs/VERIFICATION_GREEN_THREADS_SPEC.md (verifier lane)

## Current state (bootstrap)
- SD-01..SD-10 complete: event contract, AHDB projection, run/work items, verifier plan/runner, mood engine,
  run orchestration, fast unit suite, doc alignment, and EventStream E2E.
- Supervisor endpoints exist for run/work item lifecycle and receipts (see supervisor/main.py).
- Verifier allowlist and plan selection exist (config/verifiers.yaml + supervisor/verifier_plan.py).
- Live supervisor flow now runs CALM → VERIFY → SKEPTICAL with verifier plan selection and receipts.

## Next step (make it obvious)
Stabilize developer/build ergonomics and environment consistency:
- Phase 0 NATS hardening: per-user subject permissions + read-only web creds (DONE 2026-01-18).
- Auth gateway stub + session issuance + passkey UI (DONE 2026-01-18).
- Sandbox runner interface (local) wired into verifier runner (DONE 2026-01-18).
- Decide package manager (npm vs yarn vs bun) and enforce lockfile policy.
- Add a single `dev` entrypoint that bootstraps Python + Node + NATS.
- Capture sandbox/deploy scaffolding docs (ops checklist + CI smoke).

## Secondary follow-ups
- Package manager standardization (npm vs yarn vs bun) and lockfile policy.
- Sandbox + deployment scaffolding (ops docs, CI, containers).

## Archive
- Legacy planning snapshot: docs/archive/PLANNING_2026-01-17.md
