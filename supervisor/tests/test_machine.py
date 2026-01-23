import asyncio
import os
import tempfile
import unittest
from pathlib import Path

from supervisor.db import EventStore
from supervisor.machine import Machine, ModeRunResult


class TestMachine(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["NATS_ENABLED"] = "0"
        fd, self.db_path = tempfile.mkstemp(prefix="choiros_machine_", suffix=".sqlite")
        os.close(fd)
        self.store = EventStore(db_path=Path(self.db_path), user_id="local")

    def tearDown(self) -> None:
        self.store.close()
        Path(self.db_path).unlink(missing_ok=True)

    def test_single_writer_serializes(self) -> None:
        started: list[str] = []
        first_started = asyncio.Event()
        allow_finish = asyncio.Event()

        async def executor(directive):
            started.append(directive.prompt)
            if directive.prompt == "first":
                first_started.set()
                await allow_finish.wait()
            return ModeRunResult(run_id=None, status="done", verifier_results=[])

        machine = Machine(store=self.store, executor=executor)

        async def run_test():
            task1 = asyncio.create_task(machine.handle_prompt("first"))
            await first_started.wait()
            task2 = asyncio.create_task(machine.handle_prompt("second"))
            await asyncio.sleep(0.05)
            self.assertEqual(started, ["first"])
            allow_finish.set()
            await task1
            await task2
            self.assertEqual(started, ["first", "second"])

        asyncio.run(run_test())

    def test_handle_event_filters_session(self) -> None:
        ran: list[str] = []

        async def executor(directive):
            ran.append(directive.prompt)
            return ModeRunResult(run_id=None, status="done", verifier_results=[])

        machine = Machine(store=self.store, executor=executor, session_id="s1")

        async def run_test():
            event = type(
                "Event",
                (),
                {
                    "event_type": "mode.start",
                    "payload": {
                        "mode": "CALM",
                        "prompt": "hello",
                        "work_item_id": "w1",
                        "session_id": "s1",
                    },
                },
            )()
            await machine.handle_event(event)
            self.assertEqual(ran, ["hello"])

            other_event = type(
                "Event",
                (),
                {
                    "event_type": "mode.start",
                    "payload": {
                        "mode": "CALM",
                        "prompt": "skip",
                        "work_item_id": "w2",
                        "session_id": "s2",
                    },
                },
            )()
            await machine.handle_event(other_event)
            self.assertEqual(ran, ["hello"])

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
