# Machine v0 Implementation Plan
Date: 2026-01-22
Owner: ChoirOS Core

## Goal
Implement the Machine + Mode orchestration loop with NATS as the canonical event log, dynamic prompt injection per Mode, single-writer scheduling, and artifact-based sharing.

## Phase 0: Contract alignment
Deliverables
- Update event contract docs and code with Machine loop event types.
- Update tests that enforce doc/code contract alignment.

Files
- docs/specs/CHOIR_EVENT_CONTRACT_SPEC.md
- supervisor/event_contract.py
- choiros/src/lib/event_contract.ts
- supervisor/tests/test_event_contract.py

## Phase 1: Machine skeleton
Deliverables
- Add Machine loop that subscribes to NATS and emits mode directives.
- Maintain per-user run registry and single-writer scheduling.
- Create a minimal directive schema for mode.start/mode.stop/mode.update.

Files
- supervisor/machine.py (new)
- supervisor/nats_client.py
- supervisor/main.py (wire Machine lifecycle)

## Phase 2: Dynamic system prompt injection
Deliverables
- Replace hardcoded system prompt with per-mode generated prompt.
- Introduce ModeConfig schema and a prompt builder (BAML or pure Python) that uses AHDB state + receipts.

Files
- supervisor/agent/harness.py
- supervisor/mode_config.py (new)
- supervisor/baml_client (prompt schema or renderer)

## Phase 3: Capability gating at tool boundary
Deliverables
- Enforce tool allowlist per Mode in AgentTools.
- Gate network and file writes based on ModeConfig.
- Emit receipt.context.footprint and tool usage receipts on each tool call.

Files
- supervisor/agent/tools.py
- supervisor/db.py

## Phase 4: Artifact pipeline
Deliverables
- Persist artifacts with content hashes and publish artifact.create events.
- Use artifact pointers in Mode outputs and receipts.
- Allow read-only Modes to access artifacts by pointer.

Files
- supervisor/verifier_runner.py
- supervisor/db.py
- api/services/artifact_store.py (if reused)

## Phase 5: AHDB proposal/attestation flow
Deliverables
- Distinguish proposed vs asserted AHDB deltas in event payloads.
- Only asserted deltas update the AHDB projection.
- Machine promotes proposals after verifier attestations.

Files
- supervisor/db.py
- supervisor/machine.py
- supervisor/tests/test_ahdb_projection.py

## Phase 6: Single-writer scheduling
Deliverables
- Machine enforces one write-capable Mode at a time.
- Read-only Modes can run concurrently.
- Mode cancellation and re-prompting supported by directive events.

Files
- supervisor/machine.py
- supervisor/main.py

## Phase 7: Worktree isolation (optional v0+)
Deliverables
- Spawn a per-Mode worktree for write-capable Modes.
- Read-only Modes use base workspace.
- Artifacts provide cross-worktree sharing; direct path sharing is disallowed.

Files
- supervisor/git_ops.py
- supervisor/machine.py
- supervisor/run_orchestrator.py

## Verification
- Add unit tests for mode directives and scheduling rules.
- Extend V-01 and V-02 to validate new event types and AHDB proposal rules.

