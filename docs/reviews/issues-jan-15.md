# Issues (Jan 15)

Status update: 2026-01-17

## Open
- [ ] CR-05 | High | Associate tool-use loop appends assistant messages per tool_use and drops trailing text, risking tool protocol drift and lost context. (File no longer present; needs re-triage.)
- [ ] CR-09 | Medium | Verify profile returns "unknown" when commands are empty; no auto-discovery of fast checks. (File no longer present; needs re-triage.)
- [ ] DOC-01 | Medium | Docs reconciliation and update work remains: move/rename new docs, add status headers, and create docs index. `docs/reviews/docs_reconciliation.md:1` (Index added; remaining doc moves/status headers pending.)

## Resolved
- [x] CR-01 | Critical | Per-connection harness instances; prevent shared websocket conversation state. `supervisor/main.py`
- [x] CR-02 | Critical | Pass source through append + use async logging in harness to avoid misrouting. `supervisor/db.py` `supervisor/agent/harness.py`
- [x] CR-03 | High | NATS rebuild replays all sources and materializes messages/tool calls; preserves nats_seq. `supervisor/db.py` `supervisor/nats_client.py`
- [x] CR-04 | High | Normalize event types consistently during rebuild/materialization. `supervisor/db.py` `supervisor/event_contract.py`
- [x] CR-06 | High | Replace wildcard CORS with explicit origins config. `supervisor/main.py`
- [x] CR-07 | Medium | Enforce workspace boundary for tool paths. `supervisor/agent/tools.py`
- [x] CR-08 | Medium | File writes logged to event store. `supervisor/agent/tools.py` `supervisor/db.py`
- [x] CR-10 | Medium | Fix .choirignore directory prefix matching. `supervisor/git_ops.py`
- [x] CR-11 | Low | Add WebSocket prompt size + rate limits. `supervisor/main.py`

## Next Focus: Close the Event Loop (Walking Skeleton)

- [x] Decide canonical event contract (subject format, event type naming, stream naming) and record it in docs + code constants. See `docs/specs/CHOIR_EVENT_CONTRACT_SPEC.md`, `supervisor/event_contract.py`, `choiros/src/lib/event_contract.ts`.
- [x] Implement the canonical contract for a single event path end-to-end (suggest `file.write`): SQLite log, NATS publish, and frontend schema.
- [x] Enable NATS in dev (remove `NATS_ENABLED=0` in `dev.sh`) and ensure WebSocket port is exposed/configured for the frontend.
- [x] Wire frontend NATS connection on app start and subscribe to the canonical subject (e.g., `choiros.{user_id}.{source}.>`).
- [x] Update `EventStream` to display real events (no auto-clear) and show connection status when offline.

## Automation & Testing

- [x] Add Playwright E2E test for EventStream NATS rendering.
- [x] Ensure NATS WebSocket config is provided via docker compose.
