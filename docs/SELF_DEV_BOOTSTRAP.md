# Self-Development Bootstrap Issues (v0)
Status: DRAFT
Date: 2026-01-17
Owner: ChoirOS Core

## Purpose
Create a single, verifier-driven issue list that bootstraps ChoirOS to self-develop against its own specs. Each issue includes its own verifier so work can be completed and validated incrementally, with spec updates gated by verifier feedback.

## Principles
- Every issue has a bounded scope and a verifier that produces a receipt or test report.
- Verifiers are selected from an allowlisted plan, not hardcoded scripts.
- Raw verifier output is stored as artifacts; only structured attestations update control state.
- Spec changes are explicit and traced to verifier feedback via receipts.

## Verifier Catalog (allowlist targets)
Each verifier is a named target that the verifier planner can select based on scope, mood, and touched paths.

- V-01-EVENT-CONTRACT: Event contract unit tests + doc sync check
- V-02-AHDB-PROJECTION: AHDB projection unit tests (SQLite rebuild)
- V-03-RUN-STATE: Run/work-item API + persistence smoke tests
- V-04-PLAN-SELECT: Verifier-plan selection unit tests
- V-05-GREEN-THREAD: Verifier runner integration test (artifact + attestation)
- V-06-MOOD-ENGINE: Mood transition guard unit tests
- V-07-AGENT-ORCH: Run orchestration integration test (CALM → VERIFY → SKEPTICAL)
- V-08-FAST-UNIT: Supervisor fast unit test suite (db/event_contract/tools)
- V-09-DOC-ALIGN: Docs index + cross-link consistency check
- V-10-E2E-EVENTSTREAM: Playwright E2E (NATS event stream UI)

## Issues

**SD-01 Extend event contract for notes/receipts/AHDB**
- Status: DONE (2026-01-17)
- Goal: Add canonical NOTE/* and RECEIPT event types and document them.
- Deliverables: Update `docs/specs/CHOIR_EVENT_CONTRACT_SPEC.md`, `supervisor/event_contract.py`, and frontend contract if needed.
- Verifier: V-01-EVENT-CONTRACT
- Receipts: EventContractReceipt (doc hash, code hash)
- Exit: Canonical types present in docs + code, unit tests pass.

**SD-02 AHDB projection storage + rebuild**
- Status: DONE (2026-01-17)
- Goal: Add AHDB tables and deterministic rebuild from event log.
- Deliverables: `supervisor/db.py` tables + projection logic; minimal tests.
- Verifier: V-02-AHDB-PROJECTION
- Receipts: ProjectionRebuildReceipt, AHDBDelta
- Exit: Rebuild matches expected AHDB state for sample event stream.

**SD-03 Run/work-item persistence + APIs**
- Status: DONE (2026-01-17)
- Goal: Introduce run/work-item records and endpoints for creation/status.
- Deliverables: DB schema + supervisor endpoints per CHOIR_HEADLESS_1P_DESIGN.
- Verifier: V-03-RUN-STATE
- Receipts: RunCreateReceipt, WorkItemReceipt
- Exit: API smoke tests pass, data persists in SQLite.

**SD-04 Verifier plan schema + selection logic**
- Status: DONE (2026-01-17)
- Goal: Allowlist verifiers via config and select plans by scope/mood.
- Deliverables: `config/verifiers.yaml`, planner module, selection tests.
- Verifier: V-04-PLAN-SELECT
- Receipts: VerifierPlanReceipt (plan id, inputs hash)
- Exit: Planner selects expected verifier IDs for given file/mood inputs.

**SD-05 Verifier runner (green thread) + attestations**
- Status: DONE (2026-01-17)
- Goal: Execute verifier plans in isolated sessions and emit attestations.
- Deliverables: Verifier runner, artifact store hook, attestation objects.
- Verifier: V-05-GREEN-THREAD
- Receipts: VerifierReceipt, AttestationReceipt
- Exit: Integration test proves artifact storage + structured report + attestation.

**SD-06 Mood state machine + deterministic guards**
- Status: DONE (2026-01-17)
- Goal: Implement mood selection from AHDB + receipts, per spec.
- Deliverables: Mood engine module + tests.
- Verifier: V-06-MOOD-ENGINE
- Receipts: MoodTransitionReceipt
- Exit: Guard tests pass for defined scenarios.

**SD-07 Orchestrated run loop (no Ralph loop)**
- Status: DONE (2026-01-17)
- Goal: Replace ad-hoc prompt loop with run orchestration: CALM → VERIFY → SKEPTICAL.
- Deliverables: Supervisor orchestration wiring + run lifecycle events.
- Verifier: V-07-AGENT-ORCH
- Receipts: RunLifecycleReceipt, VerifierResults
- Exit: Integration test demonstrates a full run flow with verification gate.

**SD-08 Fast unit test suite for supervisor**
- Status: DONE (2026-01-17)
- Goal: Add fast tests so verifier plans can choose “cheap” checks.
- Deliverables: `supervisor/tests/` covering db/event_contract/tools.
- Verifier: V-08-FAST-UNIT
- Receipts: TestSuiteReceipt (suite id, results)
- Exit: Fast unit suite passes and is selectable by planner.

**SD-09 Docs alignment + deprecate Ralph loop references**
- Status: DONE (2026-01-17)
- Goal: Align docs with AHDB/mood state machine and remove Ralph loop assumptions.
- Deliverables: Update `docs/ARCHITECTURE.md` (if present) and indices.
- Verifier: V-09-DOC-ALIGN
- Receipts: DocUpdateReceipt (doc hashes)
- Exit: Doc cross-links consistent, no stale Ralph loop guidance.

**SD-10 End-to-end event stream verification**
- Status: DONE (2026-01-17)
- Goal: Keep UI/NATS event stream green as the system evolves.
- Deliverables: Existing Playwright E2E remains in allowlist.
- Verifier: V-10-E2E-EVENTSTREAM
- Receipts: E2EReceipt (run id, artifact hash)
- Exit: E2E passes without manual intervention.

## Spec Feedback Loop
When a verifier fails in any SD-* issue:
- Emit NOTE/HYPOTHESIS + NOTE/HYPERTHESIS with discriminating tests.
- File SPEC_CHANGE_REQUEST event if spec ambiguity caused failure.
- Only merge spec updates after a verifier (V-09-DOC-ALIGN) confirms coherence.

## Definition of Done (for each issue)
- Deliverables merged
- Assigned verifier passes
- Receipts recorded and referenced in issue log
