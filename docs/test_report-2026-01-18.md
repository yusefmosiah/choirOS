# Test Report (2026-01-18)

## Summary
- Added sandbox lifecycle, sprites adapter, and supervisor endpoint tests.
- Added contract-style checks that assert sprites adapter request payloads against a local mock server (not the real sprites API).

## Environment
- OS: macOS
- Python: 3.14 (venv at `api/venv`)
- PYTHONPATH: repo root

## Tests Run
```
source api/venv/bin/activate
PYTHONPATH=/Users/wiz/conductor/workspaces/choirOS/monterrey python -m unittest \
  supervisor.tests.test_sandbox_runner \
  supervisor.tests.test_sprites_adapter \
  supervisor.tests.test_sandbox_provider \
  supervisor.tests.test_supervisor_git_endpoints \
  supervisor.tests.test_supervisor_sandbox_endpoints \
  supervisor.tests.test_run_orchestrator \
  supervisor.tests.test_verifier_runner \
  supervisor.tests.test_sprites_live
```

## Results
- 19 tests executed, all passed.

## Notes
- Sprites adapter payloads were validated against the mock HTTP server in `supervisor/tests/test_sprites_adapter.py`.
- Live sprites test (`supervisor/tests/test_sprites_live.py`) passed using `SPRITES_API_TOKEN` from `api/.env` and now covers exec + checkpoint/restore + proxy.
- Background exec over websockets can be enabled by setting `SPRITES_WS_EXEC_LIVE=1`.
