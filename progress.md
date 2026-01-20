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
