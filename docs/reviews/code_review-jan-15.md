# Code Review (Jan 15)

## Scope
Reviewed the supervisor runtime and agent loop implementation:
- `supervisor/main.py`
- `supervisor/agent/*`
- `supervisor/db.py`
- `supervisor/nats_client.py`
- `supervisor/git_ops.py`
- `supervisor/file_history.py`
- `supervisor/vite_manager.py`

No tests were run.

## Findings (ordered by severity)

### Critical
1) Shared agent state across websocket sessions
- `agent_harness` is a single global `RalphLoop`, so all websocket clients share one conversation_id and tool state. This risks cross-user leakage and interleaved runs in multi-session use.
- Evidence: `supervisor/main.py:51`, `supervisor/main.py:212`, `supervisor/agent/ralph_loop.py:15`

2) NATS source attribution lost on synchronous append
- `EventStore.append()` schedules `_append_async_background()` which always uses `source="system"`, so user/agent events are published on the wrong NATS subjects and streams.
- Evidence: `supervisor/db.py:169`, `supervisor/db.py:192`, `supervisor/db.py:351`

### High
3) NATS rebuild drops agent/system streams and non-file events
- `rebuild_from_nats` only reads `USER_EVENTS`, so agent/system events are never replayed. `_materialize_event` only handles `file_write` and `file_delete`, so messages/tool calls are lost.
- Evidence: `supervisor/db.py:243`, `supervisor/db.py:280`, `supervisor/nats_client.py:80`

4) Event type normalization inconsistent between local append and NATS rebuild
- Local appends store `file.write` while NATS replay writes `file_write`, breaking type filters and any downstream assumptions about dot-delimited types.
- Evidence: `supervisor/db.py:138`, `supervisor/db.py:280`, `supervisor/db.py:451`

5) Tool-use response assembly risks protocol drift and lost context
- The Associate appends assistant messages per tool_use block and resets `assistant_content`, so text after tool_use isn’t included in the assistant message fed back to the model. This can desync tool-result sequencing and degrade context.
- Evidence: `supervisor/agent/associate.py:201`, `supervisor/agent/associate.py:252`, `supervisor/agent/associate.py:263`

6) CORS wildcard with credentials enabled
- `allow_origins=["*"]` + `allow_credentials=True` is invalid in browsers and unsafe for any non-local deployment.
- Evidence: `supervisor/main.py:113`

### Medium
7) Tool layer has no workspace boundary
- `_resolve_path` allows absolute paths and uses repo root as `app_dir`, enabling reads/writes outside intended workspace.
- Evidence: `supervisor/agent/tools.py:206`

8) File writes are not logged as events
- `AgentTools.write_file` and `edit_file` don’t call `EventStore.log_file_write`, so state projections miss file mutations.
- Evidence: `supervisor/agent/tools.py:241`, `supervisor/db.py:451`

9) Verify profile defaults to "unknown" with no auto-discovery
- When `VerifyProfile.commands` is empty, verification returns `unknown` instead of running a fast default check (per docs expectations).
- Evidence: `supervisor/agent/associate.py:85`

10) .choirignore prefix matching can over-match and under-match
- The prefix check treats `node_modulesx` as ignored and doesn’t ignore nested `foo/node_modules/...` paths.
- Evidence: `supervisor/git_ops.py:102`

### Low
11) Websocket prompt loop has no basic rate/size guard
- Large prompts or rapid messages can exhaust memory/compute with no throttling.
- Evidence: `supervisor/main.py:212`

## Notes
- The legacy `supervisor/agent/harness.py` remains in tree but is unused by `RalphLoop`; consider clarifying ownership or deprecating to avoid confusion.
