# Test Report - 2026-01-17 (Self-Dev Bootstrap)

## Scope
- SD-01: Event contract NOTE/RECEIPT normalization + spec alignment
- SD-02: AHDB projection storage + deterministic rebuild
- SD-03: Run/work-item persistence + APIs (store layer + projection)
- SD-04: Verifier plan config + selection logic
- SD-05: Verifier runner (green thread) + attestations
- SD-06: Mood state machine + deterministic guards
- SD-07: Run orchestration (CALM → VERIFY → SKEPTICAL)
- SD-08: Fast supervisor unit suite (db/event_contract/tools)
- SD-09: Docs alignment + deprecate Ralph loop references
- SD-10: End-to-end event stream verification (Playwright + NATS)

## Environment
- Repo: /Users/wiz/conductor/workspaces/choirOS/taipei
- Python venv: api/venv
- PYTHONPATH: repo root
- Node deps: installed via `./scripts/setup.sh --skip-python`

## Tests Run
1) Event contract unit tests (unittest)
```
source api/venv/bin/activate
PYTHONPATH="$PWD" python -m unittest supervisor.tests.test_event_contract
```

2) AHDB projection tests (unittest)
```
source api/venv/bin/activate
PYTHONPATH="$PWD" python -m unittest supervisor.tests.test_ahdb_projection
```

3) Run/work-item persistence tests (unittest)
```
source api/venv/bin/activate
PYTHONPATH="$PWD" python -m unittest supervisor.tests.test_runs
```

4) Verifier plan selection tests (unittest)
```
source api/venv/bin/activate
PYTHONPATH="$PWD" python -m unittest supervisor.tests.test_verifier_plan
```

5) Verifier runner integration tests (unittest)
```
source api/venv/bin/activate
PYTHONPATH="$PWD" python -m unittest supervisor.tests.test_verifier_runner
```

6) Mood engine guard tests (unittest)
```
source api/venv/bin/activate
PYTHONPATH="$PWD" python -m unittest supervisor.tests.test_mood_engine
```

7) Run orchestration integration tests (unittest)
```
source api/venv/bin/activate
PYTHONPATH="$PWD" python -m unittest supervisor.tests.test_run_orchestrator
```

8) Agent tools unit tests (unittest)
```
source api/venv/bin/activate
PYTHONPATH="$PWD" python -m unittest supervisor.tests.test_tools
```

9) Docs alignment check (unittest)
```
source api/venv/bin/activate
PYTHONPATH="$PWD" python -m unittest supervisor.tests.test_doc_alignment
```

10) EventStream E2E (Playwright + NATS)
```
./scripts/test.sh
```

11) Combined fast supervisor unit checks (unittest)
```
source api/venv/bin/activate
PYTHONPATH="$PWD" python -m unittest supervisor.tests.test_event_contract supervisor.tests.test_ahdb_projection supervisor.tests.test_runs supervisor.tests.test_verifier_plan supervisor.tests.test_verifier_runner supervisor.tests.test_mood_engine supervisor.tests.test_run_orchestrator supervisor.tests.test_tools
```

## Results
- PASS: event contract normalization + spec sync
- PASS: AHDB projection rebuild + log_ahdb_delta updates
- PASS: run/work item persistence + run notes/verifications/commit requests
- PASS: verifier plan selection + allowlist config parsing
- PASS: verifier runner emits artifacts + attestations
- PASS: mood guard selection + transitions
- PASS: run orchestration CALM → VERIFY → SKEPTICAL
- PASS: agent tools read/write/edit behavior
- PASS: docs index entries resolve
- PASS: EventStream renders file.write events from NATS (Playwright)
- PASS: combined supervisor unit checks
