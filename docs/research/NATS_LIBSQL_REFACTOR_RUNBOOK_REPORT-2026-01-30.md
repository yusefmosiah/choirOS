# NATS + libsql Refactor Runbook Report (2026-01-30)

## Scope
Implemented the NATS-first + libsql projection refactor per runbook, fixed consumer config issues, and ran decision tests on the one-user stack.

## Architecture Outcome
- NATS JetStream is the system of truth for events.
- Projection writes are centralized in `projector_worker.py` (single writer).
- Runtime (Machine + tools) emits events only; no projection writes.
- Runtime dedupe + ephemeral state moved to `RuntimeStore`.

## Implementation Highlights
- Split EventStore into:
  - `EventPublisher` (NATS-only publishing)
  - `ProjectionStore` (libsql/SQLite projection)
  - `RuntimeStore` (dedupe + runtime_state)
- Machine now consumes `run.input` from NATS and publishes run lifecycle events.
- Projector consumes JetStream and materializes projections (`last_nats_seq` tracking).
- Added projection rebuild utility and HTTP endpoint.
- Fixed NATS `ConsumerConfig` usage to use seconds (not nanoseconds) for `ack_wait` and `backoff`.
- Added runbook tooling:
  - `scripts/runbook_decision_tests.py`
  - `scripts/runbook_machine_runner.py`

## Decision Tests (Runbook)
### 1) 100 concurrent prompts
- **Method:** emit 100 `run.input` events; verify `run.finished` via projection.
- **Result:** 100/100 completed.
- **Note:** used no-op executor in `runbook_machine_runner.py` to validate event pipeline without LLM calls.

### 2) Supervisor restart during run
- **Method:** run machine with artificial delay, kill mid-run, restart, verify `run.finished` after redelivery.
- **Result:** run recovered and completed after restart.

### 3) Projection rebuild
- **Method:** drop projection, replay from NATS, compare counts.
- **Result:** 2,491 events replayed; counts matched pre-rebuild (events/runs/work_items/run_inputs).

## Known Gaps
- Machine lifecycle is still tied to WebSocket sessions in production; a dedicated Machine service is recommended for continuous run handling.
- Decision tests used a no-op executor (no artifacts or tool calls) to keep tests deterministic.

## Files Added/Updated (Runbook-relevant)
- `supervisor/event_publisher.py`
- `supervisor/runtime_store.py`
- `supervisor/projection_rebuild.py`
- `supervisor/projector_worker.py`
- `supervisor/machine.py`
- `supervisor/db.py`
- `scripts/runbook_decision_tests.py`
- `scripts/runbook_machine_runner.py`
- `docs/test_report-2026-01-30.md`

## Next Steps
- Run decision tests with full agent execution once provider credentials are available.
- Promote projector + machine runners to managed services (not websocket-scoped).
