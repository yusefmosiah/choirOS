# PREDICTION / EXPERIMENT / OBSERVE Pattern

This document demonstrates the PREDICTION/EXPERIMENT/OBSERVE pattern used throughout ChoirOS.

## The Core Insight

**PREDICTION/EXPERIMENT/OBSERVE is how agents learn.**

Without explicit prediction and observation, code is just movement, not learning. When we structure work as:
- **PREDICTION**: Hypothesis about what will change
- **EXPERIMENT**: Concrete action to test hypothesis
- **OBSERVE**: Explicit verification method

We're creating a **hypothesis tracking protocol** that agents can parse, execute, verify, and build upon.

## Why This Matters

The previous agent's NATS fix didn't include tests because the prompt asked for "action," not "experiment."

**Action without observation = movement, not learning.**

Every feature we build should be an experiment. Every feature should include its own verification.

## Pattern Template

```python
def test_feature_name():
    """
    PREDICTION: [Clear hypothesis about what will happen]
    What will change? What behavior will emerge? What's the expected outcome?

    EXPERIMENT: [Concrete steps to test the hypothesis]
    1. Setup: Create test data, initialize state
    2. Execute: Run the code being tested
    3. Cleanup: Remove test artifacts

    OBSERVE: [Explicit verification that prediction was correct]
    - Concrete assertion 1
    - Concrete assertion 2
    - Edge cases covered
    """
```

## Real Examples

### Example 1: NATS Deduplication (from `/Users/wiz/choirOS/supervisor/tests/test_event_dedupe.py`)

```python
def test_comprehensive_dedup_workflow(self) -> None:
    """
    PREDICTION: A complete event processing workflow with simulated failures
    demonstrates exactly-once semantics across multiple deliveries.

    EXPERIMENT:
    1. Simulate 10 events being delivered to a consumer
    2. First 5 events: process successfully (status='received' -> 'processing' -> 'done')
    3. Events 6-10: redelivered before ACK (delivery_count=2)
    4. Verify dedupe table prevents reprocessing
    5. Query aggregate metrics

    OBSERVE:
    - 10 unique events in events table (no duplicates)
    - event_dedupe table shows: 5 with delivery_count=1, 5 with delivery_count=2
    - All 10 events have status='done'
    - Zero duplicate work items or processing artifacts
    """
    num_events = 10

    for i in range(num_events):
        event_id = f"event-{i}"
        nats_seq = i + 1

        # First delivery
        is_new, status = self.store.record_event_delivery(
            consumer="test-worker",
            event_id=event_id,
            nats_seq=nats_seq,
            subject=f"choiros.local.system.mode.start",
            delivery_count=1,
        )
        self.assertTrue(is_new)
        self.assertEqual(status, "received")

        # Simulate processing
        self.store.mark_event_processing("test-worker", event_id)
        self.store.mark_event_done("test-worker", event_id)

        # Apply event to projection
        self.store.apply_event(
            "mode.start",
            {"work_item_id": f"w{i}"},
            int(time.time() * 1000),
            nats_seq=nats_seq,
            event_id=event_id,
        )

    # Simulate redelivery for events 5-9 (consumer crashed and restarted)
    for i in range(5, 10):
        event_id = f"event-{i}"
        nats_seq = i + 1

        # Second delivery (should detect already done)
        is_new, status = self.store.record_event_delivery(
            consumer="test-worker",
            event_id=event_id,
            nats_seq=nats_seq,
            subject=f"choiros.local.system.mode.start",
            delivery_count=2,
        )
        self.assertFalse(is_new, f"Event {event_id} should not be new on redelivery")
        self.assertEqual(status, "done", f"Event {event_id} should already be done")

    # Verify: No duplicate events in projection
    event_count = self.store.conn.execute(
        "SELECT COUNT(*) FROM events WHERE nats_seq BETWEEN 1 AND ?",
        (num_events,),
    ).fetchone()[0]
    self.assertEqual(event_count, num_events, "Should have exactly 10 events, no duplicates")

    # Verify: Dedupe table tracks all deliveries correctly
    dedupe_rows = self.store.conn.execute(
        "SELECT event_id, status, delivery_count FROM event_dedupe WHERE consumer = ? ORDER BY event_id",
        ("test-worker",),
    ).fetchall()

    self.assertEqual(len(dedupe_rows), num_events, "Should have 10 dedupe records")

    delivery_counts = [row["delivery_count"] for row in dedupe_rows]
    self.assertEqual(sum(1 for dc in delivery_counts if dc == 1), 5, "5 events delivered once")
    self.assertEqual(sum(1 for dc in delivery_counts if dc == 2), 5, "5 events delivered twice")

    # Verify: All events marked as done
    for row in dedupe_rows:
        self.assertEqual(row["status"], "done", f"Event {row['event_id']} should be done")
```

### Example 2: NATS Message Deduplication (from `/Users/wiz/choirOS/supervisor/tests/test_nats_integration.py`)

```python
def test_publish_dedup_by_msg_id(self) -> None:
    """
    PREDICTION: Publishing the same event (same event_id) twice to NATS JetStream
    results in exactly one message stored due to NATS message ID deduplication.

    EXPERIMENT:
    1. Create ChoirEvent with unique event_id
    2. Publish to NATS JetStream twice with same event_id
    3. Fetch events from stream
    4. Count occurrences by event_id

    OBSERVE:
    - Exactly one event with matching event_id in stream
    - Second publish is silently ignored by NATS
    - No duplicate events in consumer fetch
    """
    async def run():
        client = NATSClient(url=_nats_url())
        await client.connect()
        info = await client.js.stream_info(CHOIR_STREAM)
        start_seq = info.state.last_seq
        user_id = f"test-{uuid.uuid4()}"
        event = ChoirEvent(
            id=str(uuid.uuid4()),
            timestamp=int(time.time() * 1000),
            user_id=user_id,
            source="system",
            event_type="mode.start",
            payload={"work_item_id": "w1"},
        )
        await client.publish_event(event)
        await client.publish_event(event)
        events = await client.get_events(
            stream=CHOIR_STREAM,
            subject_filter=subject_prefix_for(user_id),
            start_seq=start_seq + 1,
            limit=10,
        )
        matches = [e for e, _ in events if e.id == event.id]
        await client.disconnect()
        self.assertEqual(len(matches), 1)

    asyncio.run(run())
```

### Example 3: Projection Idempotence (from `/Users/wiz/choirOS/supervisor/tests/test_event_dedupe.py`)

```python
def test_apply_event_dedupes_by_nats_seq(self) -> None:
    """
    PREDICTION: Applying events with the same nats_seq results in exactly one
    row in the events table, making event projection idempotent.

    EXPERIMENT:
    1. Apply event with nats_seq=5, event_id="event-1"
    2. Apply different event with same nats_seq=5, event_id="event-2"
    3. Query events table for nats_seq=5

    OBSERVE:
    - Both apply_event calls return the same seq (first insert)
    - Only one row with nats_seq=5 in events table
    - Second apply_event is a no-op due to nats_seq unique constraint
    """
    now_ms = int(time.time() * 1000)
    first = self.store.apply_event(
        "mode.start",
        {"work_item_id": "w1"},
        now_ms,
        nats_seq=5,
        event_id="event-1",
    )
    second = self.store.apply_event(
        "mode.start",
        {"work_item_id": "w1"},
        now_ms,
        nats_seq=5,
        event_id="event-2",
    )
    self.assertEqual(first, second)
    count = self.store.conn.execute("SELECT COUNT(*) FROM events WHERE nats_seq = 5").fetchone()[0]
    self.assertEqual(count, 1)
```

## Required Elements

Every test file for new features MUST include:

1. **Module-level docstring** explaining the overall hypothesis
2. **Each test method** with PREDICTION/EXPERIMENT/OBSERVE sections
3. **Edge cases** explicitly covered in OBSERVE section
4. **Metrics or concrete assertions** (not "should work" but "count == 1")

## Implementation Workflow

When implementing ANY feature or fix:

1. **Write the PREDICTION first** (what are you trying to achieve?)
2. **Write the OBSERVE section next** (how will you prove it works?)
3. **Implement the EXPERIMENT** (the code + test)
4. **Run the test** to verify your prediction

## Why This Works

- **Machine-Actionable**: Agents can parse PREDICTION/EXPERIMENT/OBSERVE blocks
- **Buildable**: Later work can reference earlier hypotheses
- **Verifiable**: Every feature includes its own proof
- **AHDB-Compatible**: Hypotheses are first-class objects in our system

This makes our codebase a knowledge graph, not just code.
