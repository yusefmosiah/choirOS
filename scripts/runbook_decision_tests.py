import argparse
import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from supervisor.event_publisher import EventPublisher
from supervisor.nats_client import get_nats_client
from supervisor.event_contract import build_subject
from supervisor.db import get_store
from supervisor.projection_rebuild import rebuild_projection_from_nats

DEFAULT_STATE_PATH = PROJECT_ROOT / ".context" / "runbook_runs.json"


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


async def emit_runs(count: int, prompt: str, user_id: str, session_id: str | None, state_path: Path) -> list[str]:
    publisher = EventPublisher(user_id=user_id)
    run_ids: list[str] = []
    for _ in range(count):
        run_id = str(uuid.uuid4())
        work_item_id = str(uuid.uuid4())
        payload = {
            "prompt": prompt,
            "input_kind": "initial",
            "work_item_id": work_item_id,
            "run_id": run_id,
        }
        if session_id:
            payload["session_id"] = session_id
        await publisher.publish("run.input", payload, source="user")
        run_ids.append(run_id)
    state = _load_state(state_path)
    state.update({"run_ids": run_ids, "user_id": user_id, "session_id": session_id, "prompt": prompt})
    _save_state(state_path, state)
    return run_ids


async def wait_for_runs(run_ids: list[str], user_id: str, timeout_s: int) -> dict:
    if not run_ids:
        return {"completed": [], "pending": []}
    pending = set(run_ids)
    completed: list[str] = []
    nats_client = await get_nats_client()
    subject = build_subject(user_id, "system", "run.finished")

    done_event = asyncio.Event()

    async def handle(event):
        run_id = (event.payload or {}).get("run_id")
        if run_id in pending:
            pending.remove(run_id)
            completed.append(run_id)
            if not pending:
                done_event.set()

    await nats_client.subscribe(subject, handle)

    try:
        await asyncio.wait_for(done_event.wait(), timeout=timeout_s)
    except asyncio.TimeoutError:
        pass

    return {"completed": completed, "pending": sorted(pending)}


async def rebuild_projection(user_id: str, to_seq: int | None, confirm: str) -> dict:
    if confirm != "REBUILD":
        return {"ok": False, "error": "confirmation required: pass --confirm REBUILD"}
    store = get_store(user_id)
    replayed = await rebuild_projection_from_nats(store, to_seq=to_seq)
    return {"ok": True, "replayed": replayed}


def verify_projection(run_ids: list[str], user_id: str) -> dict:
    if not run_ids:
        return {"total": 0, "finished": 0, "missing": 0}
    store = get_store(user_id)
    cursor = store.conn.execute("SELECT payload FROM events WHERE type = ?", ("run.finished",))
    finished = set()
    run_id_set = set(run_ids)
    for row in cursor.fetchall():
        payload = json.loads(row["payload"])
        run_id = payload.get("run_id")
        if run_id in run_id_set:
            finished.add(run_id)
    missing = sorted(run_id_set - finished)
    return {"total": len(run_id_set), "finished": len(finished), "missing": len(missing), "missing_ids": missing}


async def main() -> None:
    parser = argparse.ArgumentParser(description="Runbook decision tests for NATS + libsql")
    sub = parser.add_subparsers(dest="command", required=True)

    emit_parser = sub.add_parser("emit")
    emit_parser.add_argument("--count", type=int, default=10)
    emit_parser.add_argument("--prompt", type=str, default="runbook decision test")
    emit_parser.add_argument("--user", type=str, default="local")
    emit_parser.add_argument("--session", type=str, default=None)
    emit_parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)

    wait_parser = sub.add_parser("wait")
    wait_parser.add_argument("--timeout", type=int, default=300)
    wait_parser.add_argument("--user", type=str, default=None)
    wait_parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)

    rebuild_parser = sub.add_parser("rebuild")
    rebuild_parser.add_argument("--user", type=str, default="local")
    rebuild_parser.add_argument("--to-seq", type=int, default=None)
    rebuild_parser.add_argument("--confirm", type=str, default="")

    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--user", type=str, default=None)
    verify_parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)

    args = parser.parse_args()

    if args.command == "emit":
        session_id = args.session
        run_ids = await emit_runs(args.count, args.prompt, args.user, session_id, args.state)
        print(json.dumps({"emitted": len(run_ids), "run_ids": run_ids, "state": str(args.state)}, indent=2))
        return

    if args.command == "wait":
        state = _load_state(args.state)
        run_ids = state.get("run_ids", [])
        user_id = args.user or state.get("user_id") or "local"
        start = time.time()
        result = await wait_for_runs(run_ids, user_id, args.timeout)
        result["elapsed_s"] = round(time.time() - start, 2)
        print(json.dumps(result, indent=2))
        return

    if args.command == "rebuild":
        result = await rebuild_projection(args.user, args.to_seq, args.confirm)
        print(json.dumps(result, indent=2))
        return

    if args.command == "verify":
        state = _load_state(args.state)
        run_ids = state.get("run_ids", [])
        user_id = args.user or state.get("user_id") or "local"
        result = verify_projection(run_ids, user_id)
        print(json.dumps(result, indent=2))
        return


if __name__ == "__main__":
    asyncio.run(main())
