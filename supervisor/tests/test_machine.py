"""
Machine Tests

PREDICTION: Machine processes run.input events exactly once, serializes execution,
selects modes from projected AHDB state, and publishes lifecycle events.

EXPERIMENT: Feed synthetic run.input messages to Machine and observe publish order.

OBSERVE: Execution order is serialized, session filtering works, and mode selection
reacts to AHDB projection updates.
"""

import asyncio
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from supervisor.db import ProjectionStore
from supervisor.event_publisher import EventPublisher
from supervisor.machine import Machine, ModeRunResult
from supervisor.nats_client import ChoirEvent
from supervisor.runtime_store import RuntimeStore
from supervisor.tests.fakes import FakeNATSClient


class _FakeMetaSeq:
    def __init__(self, stream: int):
        self.stream = stream


class _FakeMetadata:
    def __init__(self, stream_seq: int, delivery: int = 1):
        self.sequence = _FakeMetaSeq(stream_seq)
        self.num_delivered = delivery
        self.stream = "CHOIR"


class _FakeMsg:
    def __init__(self, event: ChoirEvent, seq: int):
        self.data = event.to_json()
        self.subject = "choiros.local.user.run.input"
        self.metadata = _FakeMetadata(seq)
        self.headers = {}
        self.acked = False
        self.nacked = False

    async def ack(self):
        self.acked = True

    async def nak(self):
        self.nacked = True


class TestMachine(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.db_path = tempfile.mkstemp(prefix="choiros_machine_", suffix=".sqlite")
        os.close(fd)
        self.projection = ProjectionStore(db_path=Path(self.db_path), user_id="local")
        self.fake_nats = FakeNATSClient()
        self.publisher = EventPublisher(user_id="local", nats_client=self.fake_nats)
        self.runtime_store = RuntimeStore(db_path=Path(self.db_path), user_id="local")

    def tearDown(self) -> None:
        self.projection.close()
        self.runtime_store.close()
        Path(self.db_path).unlink(missing_ok=True)

    def test_serializes_run_inputs(self) -> None:
        """
        PREDICTION: Concurrent run.input messages are processed sequentially by the
        machine's writer lock.

        EXPERIMENT:
        1. Create two run.input events and feed them concurrently to _handle_input_message
        2. Block the first execution before allowing the second to proceed

        OBSERVE:
        - The second prompt does not start until the first finishes
        - Finished order matches input order
        """
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

        machine = Machine(
            projection=self.projection,
            publisher=self.publisher,
            executor=executor,
            session_id="s1",
            runtime_store=self.runtime_store,
        )

        async def run_test():
            now_ms = int(datetime.now().timestamp() * 1000)
            event1 = ChoirEvent(
                id="event-1",
                timestamp=now_ms,
                user_id="local",
                source="user",
                event_type="run.input",
                payload={"prompt": "first", "work_item_id": "w1", "run_id": "r1", "session_id": "s1"},
            )
            event2 = ChoirEvent(
                id="event-2",
                timestamp=now_ms,
                user_id="local",
                source="user",
                event_type="run.input",
                payload={"prompt": "second", "work_item_id": "w2", "run_id": "r2", "session_id": "s1"},
            )
            msg1 = _FakeMsg(event1, 1)
            msg2 = _FakeMsg(event2, 2)

            task = asyncio.gather(
                machine._handle_input_message(msg1, "consumer"),
                machine._handle_input_message(msg2, "consumer"),
            )

            await asyncio.wait_for(first_started.wait(), timeout=1.0)
            self.assertEqual(started, ["first"])
            self.assertNotIn("second", started)

            allow_finish.set()
            await asyncio.wait_for(task, timeout=2.0)
            self.assertEqual(finished, ["first", "second"])

        asyncio.run(run_test())

    def test_session_filter_skips_other_sessions(self) -> None:
        """
        PREDICTION: A run.input event with a mismatched session_id is acknowledged
        without executing the run.

        EXPERIMENT:
        1. Send a run.input event with a different session_id
        2. Observe executor not called and message acked

        OBSERVE:
        - No execution occurs
        - Message is acknowledged
        """
        ran: list[str] = []

        async def executor(directive):
            ran.append(directive.prompt)
            return ModeRunResult(run_id=None, status="done", verifier_results=[])

        machine = Machine(
            projection=self.projection,
            publisher=self.publisher,
            executor=executor,
            session_id="s1",
            runtime_store=self.runtime_store,
        )

        async def run_test():
            now_ms = int(datetime.now().timestamp() * 1000)
            event = ChoirEvent(
                id="event-x",
                timestamp=now_ms,
                user_id="local",
                source="user",
                event_type="run.input",
                payload={"prompt": "skip", "work_item_id": "w9", "run_id": "r9", "session_id": "s2"},
            )
            msg = _FakeMsg(event, 9)
            await machine._handle_input_message(msg, "consumer")
            self.assertEqual(ran, [])
            self.assertTrue(msg.acked)

        asyncio.run(run_test())

    def test_select_mode_from_ahdb(self) -> None:
        """
        PREDICTION: Mode selection reflects AHDB state in the projection store.

        EXPERIMENT:
        1. Apply AHDB delta events for conjectures and crashes
        2. Re-evaluate selected mode

        OBSERVE:
        - Conjectures yield CALM
        - Crash yields CONTRITE
        - Repeated failures yield SKEPTICAL
        """
        async def executor(directive):
            return ModeRunResult(run_id=None, status="done", verifier_results=[])

        machine = Machine(
            projection=self.projection,
            publisher=self.publisher,
            executor=executor,
            runtime_store=self.runtime_store,
        )

        config = machine._select_mode("test prompt")
        self.assertEqual(config.mode_id, "CURIOUS")

        now_ms = int(datetime.now().timestamp() * 1000)
        self.projection.apply_event(
            "receipt.ahdb.delta",
            {"delta": {"conjectures": ["c1", "c2"]}, "authority": "asserted"},
            now_ms,
        )
        self.projection.conn.commit()
        config = machine._select_mode("test prompt")
        self.assertEqual(config.mode_id, "CALM")

        self.projection.apply_event(
            "receipt.ahdb.delta",
            {"delta": {"crash_detected": True}, "authority": "asserted"},
            now_ms,
        )
        self.projection.conn.commit()
        config = machine._select_mode("test prompt")
        self.assertEqual(config.mode_id, "CONTRITE")

        self.projection.apply_event(
            "receipt.ahdb.delta",
            {"delta": {"crash_detected": False, "repeated_verifier_failures": True}, "authority": "asserted"},
            now_ms,
        )
        self.projection.conn.commit()
        config = machine._select_mode("test prompt")
        self.assertEqual(config.mode_id, "SKEPTICAL")


if __name__ == "__main__":
    unittest.main()
