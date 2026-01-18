# Progress (2026-01-18)

## Completed
- Sandbox lifecycle endpoints (create/exec/process stop/proxy/checkpoint/restore/destroy).
- FE bootstrap for sandboxed frontend (`/frontend/url` + redirect when `VITE_FRONTEND_SANDBOX=1`).
- Terminal app wired to `/sandbox/exec` and `/sandbox/process/stop`.
- Sprites adapter aligned to the published API contract (v1 sprites endpoints, exec query params, checkpoint/restore, kill session).

## Tests
- Unit and integration tests run; see `docs/test_report-2026-01-18.md`.
- Live sprites test passed with token from `api/.env`.
- Live sprites test now validates exec + checkpoint/restore + proxy; background exec optional via `SPRITES_WS_EXEC_LIVE=1`.

## Next Steps
- Provide a valid `SPRITES_API_TOKEN` (or `SPRITES_TOKEN`) and re-run `supervisor.tests.test_sprites_live`.
- Validate sprites API response fields in live mode; adjust adapter if any contract mismatches appear.
- Wire terminal streaming output for background exec sessions (WS attach) once live exec is verified.
