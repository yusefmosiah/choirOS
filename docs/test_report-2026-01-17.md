# Test Report - 2026-01-17

## Scope
- Implement canonical event contract for `file.write` end-to-end
- Enable NATS in dev + WebSocket port exposure
- Wire frontend NATS connection + canonical subscription

## Environment
- Repo: /Users/wiz/conductor/workspaces/choirOS/buffalo
- Python venv: api/venv (created for this run)
- PYTHONPATH: repo root

## Tests Run
1) Python smoke test: event contract helpers + SQLite logging
```
source api/venv/bin/activate
PYTHONPATH="$PWD" python - <<'PY'
import os
import tempfile
from pathlib import Path

os.environ["NATS_ENABLED"] = "0"

from supervisor.db import EventStore
from supervisor.event_contract import build_subject, normalize_event_type

assert build_subject("local", "agent", "file.write") == "choiros.local.agent.file.write"
assert normalize_event_type("FILE_WRITE") == "file.write"
assert normalize_event_type("tool_call") == "tool.call"
assert normalize_event_type("file.write") == "file.write"

fd, db_path = tempfile.mkstemp(prefix="choiros_test_", suffix=".sqlite")
os.close(fd)
store = EventStore(db_path=Path(db_path), user_id="local")
store.log_file_write("tmp/hello.txt", b"hello")
row = store.get_events(event_type="file.write")[-1]
assert row["type"] == "file.write"
store.close()
Path(db_path).unlink(missing_ok=True)

print("OK: event contract helpers + file.write SQLite log")
PY
```

2) NATS integration test: JetStream publish/subscribe for `file.write`
```
source api/venv/bin/activate
PYTHONPATH="$PWD" NATS_ENABLED=1 python - <<'PY'
import asyncio
from pathlib import Path

from supervisor.db import EventStore
from supervisor.nats_client import get_nats_client, close_nats_client

async def main():
    client = await get_nats_client()
    received = asyncio.Future()

    async def cb(event):
        if event.event_type == "file.write" and not received.done():
            received.set_result(event)

    await client.subscribe("choiros.local.>", cb)

    store = EventStore(db_path=Path(".context/test_state.sqlite"), user_id="local")
    await store.log_file_write_async("tmp/test.txt", b"hello")

    event = await asyncio.wait_for(received, 5)
    assert event.event_type == "file.write"
    assert event.payload.get("path") == "tmp/test.txt"
    print("OK: NATS file.write publish/subscribe", event.payload)

    store.close()
    await close_nats_client()

asyncio.run(main())
PY
```

3) EventStream E2E (Playwright + NATS)
```
cd choiros
npm run test:e2e
```

## Results
- PASS: event contract helpers and SQLite `file.write` logging
- PASS: NATS JetStream publish/subscribe for `file.write`
- PASS: EventStream renders `file.write` events from NATS (Playwright)

## Follow-ups
- None.
