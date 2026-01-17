# Issues (Jan 15)

- CR-01 | Critical | Shared RalphLoop across websocket sessions leaks conversation state and interleaves runs; create per-connection/per-user harness instances. `supervisor/main.py:51` `supervisor/main.py:212` `supervisor/agent/ralph_loop.py:15`
- CR-02 | Critical | NATS publish from `EventStore.append` hardcodes source="system", misrouting user/agent events; pass source or use append_async everywhere. `supervisor/db.py:169` `supervisor/db.py:192` `supervisor/db.py:351`
- CR-03 | High | NATS rebuild only replays USER_EVENTS and materializes file_* events, dropping agent/system streams, messages, and tool calls. `supervisor/db.py:243` `supervisor/db.py:280` `supervisor/nats_client.py:80`
- CR-04 | High | Event type normalization mismatch (file.write vs file_write) between local append and rebuild; breaks filters and projections. `supervisor/db.py:138` `supervisor/db.py:280` `supervisor/db.py:451`
- CR-05 | High | Associate tool-use loop appends assistant messages per tool_use and drops trailing text, risking tool protocol drift and lost context. `supervisor/agent/associate.py:201` `supervisor/agent/associate.py:252` `supervisor/agent/associate.py:263`
- CR-06 | High | CORS wildcard with credentials enabled; unsafe and invalid for browsers. `supervisor/main.py:113`
- CR-07 | Medium | Tool layer allows absolute paths and repo-root writes; no workspace boundary enforcement. `supervisor/agent/tools.py:206`
- CR-08 | Medium | File writes are not logged to the event store; projections and receipts miss file changes. `supervisor/agent/tools.py:241` `supervisor/db.py:451`
- CR-09 | Medium | Verify profile returns "unknown" when commands are empty; no auto-discovery of fast checks. `supervisor/agent/associate.py:85`
- CR-10 | Medium | .choirignore prefix matching can over-match (node_modulesx) and miss nested directories. `supervisor/git_ops.py:102`
- CR-11 | Low | Websocket prompt loop lacks size/rate limits; potential resource exhaustion. `supervisor/main.py:212`
- DOC-01 | Medium | Docs reconciliation and update work remains: move/rename new docs, add status headers, and create docs index. `docs/docs_reconciliation.md:1`

## Next Focus: Close the Event Loop (Walking Skeleton)

- [x] Decide canonical event contract (subject format, event type naming, stream naming) and record it in docs + code constants. See `docs/specs/CHOIR_EVENT_CONTRACT_SPEC.md`, `supervisor/event_contract.py`, `choiros/src/lib/event_contract.ts`.
- [x] Implement the canonical contract for a single event path end-to-end (suggest `file.write`): SQLite log, NATS publish, and frontend schema.
- [x] Enable NATS in dev (remove `NATS_ENABLED=0` in `dev.sh`) and ensure WebSocket port is exposed/configured for the frontend.
- [x] Wire frontend NATS connection on app start and subscribe to the canonical subject (e.g., `choiros.{user_id}.{source}.>`).
- [x] Update `EventStream` to display real events (no auto-clear) and show connection status when offline.

## Automation & Testing

- [x] Add Playwright E2E test for EventStream NATS rendering.
- [x] Ensure NATS WebSocket config is provided via docker compose.
