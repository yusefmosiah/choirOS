# Progress (2026-01-20)

## Completed
- Sandbox lifecycle endpoints (create/exec/process stop/proxy/checkpoint/restore/destroy).
- FE bootstrap for sandboxed frontend (`/frontend/url` + redirect when `VITE_FRONTEND_SANDBOX=1`).
- Terminal app wired to `/sandbox/exec` and `/sandbox/process/stop`.
- Sprites adapter aligned to the published API contract.
- **BAML Phase 1**: `VerifierRunner` uses BAML for structured analysis (`VerifierOutcome`).
- **BAML Phase 2**: Tool schemas + agent functions (`PlanAction`, `SynthesizeResponse`, `AssessTask`).
- **BAML Phase 3**: `RunOrchestrator` uses BAML `AssessTask` for intelligent verification gating.

## Tests
- Unit and integration tests run; 3/3 orchestrator tests passing.
- Live sprites test passed with token from `api/.env`.
- BAML functions tested with live Claude 4.5 Opus via AWS Bedrock.

## Next Steps
- Wire terminal streaming output for background exec sessions.
- Consider docs-updating as a green thread process (per user feedback).

# Progress (2026-01-23)

## Completed
- Machine v0 contract + implementation plan authored and indexed.
- Event contract extended with mode directives + artifact events.
- Machine control plane added with single-writer scheduling and directive handling.
- Dynamic system prompt injection per mode; mode changes reset context.
- Tool capability gating (write/network) enforced at tool boundary with receipts.
- Artifact pipeline: diffs + bash logs stored as artifacts with pointer events.
- AHDB proposal vs asserted flow and new proposal table.
- WebSocket flow now emits mode.start events when NATS is available.
- New tests for machine scheduling, directive filtering, artifacts, and AHDB proposals.

## Tests
- `python -m unittest supervisor.tests.test_event_contract supervisor.tests.test_ahdb_projection supervisor.tests.test_runs supervisor.tests.test_verifier_plan supervisor.tests.test_verifier_runner supervisor.tests.test_mood_engine supervisor.tests.test_run_orchestrator supervisor.tests.test_tools supervisor.tests.test_machine`
- Note: BAML analysis warns about `baml-py==0.217.0` but tests pass.

## Next Steps
- Implement NATS-driven mode execution outside WS (headless runner).
- Add artifact.pointer usage in UI (audits, diffs, verifier logs).
- Add minimal AHDB proposal emitter in modes and promotion policy tests.

# Progress (2026-01-23b)

## Completed
- NATS credentials can be fetched without a session when auth is disabled (local dev).
- Frontend now attempts NATS creds even without a session token.
- Writer audit stream shows blind spots + citations and labels tone instead of mood.
- Mode directives can be consumed via NATS when available.
- Artifact pointers can be read via new read_artifact tool.

## Tests
- `python -m unittest supervisor.tests.test_event_contract supervisor.tests.test_ahdb_projection supervisor.tests.test_runs supervisor.tests.test_verifier_plan supervisor.tests.test_verifier_runner supervisor.tests.test_mood_engine supervisor.tests.test_run_orchestrator supervisor.tests.test_tools supervisor.tests.test_machine`

## Next Steps
- Investigate NATS offline toast in UI once dev server is running with new auth fallback.
- Extend auditor into a multi-pass research loop with retrieval + citations.

## Notes
- Architecture direction confirmed: Machine (outer) must not perform research; it spawns Mode workers for all retrieval/analysis.
- Command bar should enqueue work items and remain responsive; execution moves to the Machine queue.

## Next Steps (updated)
- Implement work-queue scheduling and non-blocking command bar flow.
- Move auditor execution into a Mode worker and implement multipass loop.
- Build visualization graph that maps receipts, artifacts, and AHDB deltas.
- Fix persistence: sandbox/worktree snapshots and projection rebuild on restart.
