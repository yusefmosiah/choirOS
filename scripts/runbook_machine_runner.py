import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from supervisor.db import get_store
from supervisor.event_publisher import get_publisher
from supervisor.machine import Machine, ModeDirective, ModeRunResult


async def main() -> None:
    parser = argparse.ArgumentParser(description="Runbook Machine listener")
    parser.add_argument("--delay", type=float, default=0.0, help="Seconds to sleep per run")
    args = parser.parse_args()
    store = get_store()
    publisher = get_publisher(store.user_id)

    async def execute_mode(directive: ModeDirective) -> ModeRunResult:
        # Minimal executor for runbook decision tests.
        if args.delay > 0:
            await asyncio.sleep(args.delay)
        return ModeRunResult(run_id=directive.run_id, status="completed", verifier_results=[])

    machine = Machine(projection=store, publisher=publisher, executor=execute_mode)
    ok = await machine.listen_for_inputs()
    if not ok:
        raise RuntimeError("Failed to start Machine listener")

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
