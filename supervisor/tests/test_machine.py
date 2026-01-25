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
        finished: list[str] = []
        first_started = asyncio.Event()
        allow_finish = asyncio.Event()

        async def executor(directive):
            started.append(directive.prompt)
            if directive.prompt == "first":
                first_started.set()
                await allow_finish.wait()
            finished.append(directive.prompt)
            return ModeRunResult(run_id=None, status="done", verifier_results=[])

        machine = Machine(store=self.store, executor=executor)

        async def run_test():
            machine.start_loop()
            # Enqueue two prompts
            await machine.handle_prompt("first")
            await machine.handle_prompt("second")
            
            # Wait for first to start
            await asyncio.wait_for(first_started.wait(), timeout=1.0)
            
            # Verify serialization: "second" should not have started yet
            self.assertEqual(started, ["first"])
            self.assertNotIn("second", started)
            
            # Allow first to finish
            allow_finish.set()
            
            # Wait for both to be processed (poll until finished has 2 items)
            for _ in range(20):
                if len(finished) == 2:
                    break
                await asyncio.sleep(0.05)
            
            self.assertEqual(finished, ["first", "second"])
            
            await machine.stop_loop()

        asyncio.run(run_test())

    def test_handle_event_filters_session(self) -> None:
        ran: list[str] = []

        async def executor(directive):
            ran.append(directive.prompt)
            return ModeRunResult(run_id=None, status="done", verifier_results=[])

        machine = Machine(store=self.store, executor=executor, session_id="s1")

        async def run_test():
            work_item = self.store.create_work_item(description="hello", status="queued")
            event = type(
                "Event",
                (),
                {
                    "event_type": "mode.start",
                    "payload": {
                        "mode": "CALM",
                        "prompt": "hello",
                        "work_item_id": work_item["id"],
                        "session_id": "s1",
                    },
                },
            )()
            await machine.handle_event(event)
            self.assertEqual(ran, [])
            updated = self.store.get_work_item(work_item["id"])
            self.assertIsNotNone(updated)
            self.assertEqual(updated["status"], "queued")

            other_item = self.store.create_work_item(description="skip", status="queued")
            other_event = type(
                "Event",
                (),
                {
                    "event_type": "mode.start",
                    "payload": {
                        "mode": "CALM",
                        "prompt": "skip",
                        "work_item_id": other_item["id"],
                        "session_id": "s2",
                    },
                },
            )()
            await machine.handle_event(other_event)
            self.assertEqual(ran, [])

        asyncio.run(run_test())

    def test_select_mode_from_ahdb(self) -> None:
        """Test that mode selection is driven by AHDB state."""
        modes_selected: list[str] = []

        async def executor(directive):
            modes_selected.append(directive.mode_id)
            return ModeRunResult(run_id=None, status="done", verifier_results=[])

        machine = Machine(store=self.store, executor=executor)

        # Empty AHDB: no conjectures -> CURIOUS (seeking context)
        config = machine._select_mode("test prompt")
        self.assertEqual(config.mode_id, "CURIOUS")

        # Set conjectures present -> CALM (normal operation)
        self.store.log_ahdb_delta(
            {"conjectures": ["c1", "c2"]},
            {"run_id": "init", "authority": "asserted"},
        )
        config = machine._select_mode("test prompt")
        self.assertEqual(config.mode_id, "CALM")

        # Set crash_detected in AHDB -> CONTRITE
        self.store.log_ahdb_delta(
            {"crash_detected": True},
            {"run_id": "test", "authority": "asserted"},
        )
        config = machine._select_mode("test prompt")
        self.assertEqual(config.mode_id, "CONTRITE")

        # Clear crash, set repeated failures -> SKEPTICAL
        self.store.log_ahdb_delta(
            {"crash_detected": False, "repeated_verifier_failures": True},
            {"run_id": "test2", "authority": "asserted"},
        )
        config = machine._select_mode("test prompt")
        self.assertEqual(config.mode_id, "SKEPTICAL")


if __name__ == "__main__":
    unittest.main()
