"""Projection rebuild utilities."""

from __future__ import annotations

from typing import Optional

from .db import ProjectionStore
from .nats_client import get_nats_client
from shared.tenancy import subject_prefix_for
from .event_contract import CHOIR_STREAM


async def rebuild_projection_from_nats(store: ProjectionStore, to_seq: Optional[int] = None) -> int:
    nats = await get_nats_client()

    store.conn.executescript(
        """
        DELETE FROM files;
        DELETE FROM messages;
        DELETE FROM tool_calls;
        DELETE FROM conversations;
        DELETE FROM ahdb_state;
        DELETE FROM ahdb_deltas;
        DELETE FROM ahdb_proposals;
        DELETE FROM run_notes;
        DELETE FROM run_verifications;
        DELETE FROM run_commit_requests;
        DELETE FROM run_inputs;
        DELETE FROM runs;
        DELETE FROM work_items;
        DELETE FROM checkpoints;
        DELETE FROM user_settings;
        DELETE FROM events;
        DELETE FROM projection_state;
        """
    )
    store.conn.commit()

    events = await nats.get_events(
        stream=CHOIR_STREAM,
        subject_filter=subject_prefix_for(store.user_id),
        start_seq=1,
        limit=to_seq or 100000,
    )

    count = 0
    last_seq = None
    for event, nats_seq in events:
        if nats_seq is None:
            continue
        store.apply_event(event.event_type, event.payload, event.timestamp, nats_seq, event.id)
        count += 1
        last_seq = nats_seq if last_seq is None else max(last_seq, nats_seq)

    if last_seq is not None:
        store.set_projection_state("last_nats_seq", str(last_seq), commit=False)
    store.conn.commit()
    return count
