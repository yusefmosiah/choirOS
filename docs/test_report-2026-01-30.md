# Test Report (2026-01-30)

## Summary
- Verified supervisor test suite after NATS consumer config fix and runbook tooling.
- Executed runbook decision tests for concurrency, restart recovery, and projection rebuild.

## Environment
- OS: macOS
- Python: 3.14 (venv at `api/venv`)
- PYTHONPATH: repo root
- NATS: local (docker)

## Tests Run
```
PYTHONPATH=/Users/wiz/choirOS /Users/wiz/choirOS/api/venv/bin/python -m pytest supervisor/tests

/Users/wiz/choirOS/api/venv/bin/python scripts/runbook_machine_runner.py --delay 0
/Users/wiz/choirOS/api/venv/bin/python scripts/runbook_decision_tests.py emit --count 100 --prompt "runbook decision test: 100 concurrent (fixed ack/backoff)"
/Users/wiz/choirOS/api/venv/bin/python scripts/runbook_decision_tests.py verify

/Users/wiz/choirOS/api/venv/bin/python scripts/runbook_machine_runner.py --delay 10
/Users/wiz/choirOS/api/venv/bin/python scripts/runbook_decision_tests.py emit --count 1 --prompt "runbook decision test: supervisor restart"
/Users/wiz/choirOS/api/venv/bin/python scripts/runbook_decision_tests.py verify

/Users/wiz/choirOS/api/venv/bin/python scripts/runbook_decision_tests.py rebuild --confirm REBUILD
```

## Results
- Pytest: 69 passed, 2 skipped.
- Decision test 1 (100 concurrent prompts): 100/100 run.finished events observed via projection verify.
- Decision test 2 (restart during run): 1/1 run.finished observed after machine restart.
- Decision test 3 (projection rebuild): 2,491 events replayed; post-rebuild counts match pre-rebuild.

## Notes
- Decision tests used `scripts/runbook_machine_runner.py` (no-op executor) to validate event pipeline and replay behavior without invoking LLMs.
