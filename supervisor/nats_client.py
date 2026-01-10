"""
NATS JetStream client for ChoirOS event sourcing.

Provides async connection management, stream creation, and event publishing.
NATS is the source of truth - SQLite is a materialized projection.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Callable, Optional
from dataclasses import dataclass, asdict

import nats
from nats.js.api import StreamConfig, ConsumerConfig, RetentionPolicy, StorageType


# Configuration
NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")


@dataclass
class ChoirEvent:
    """Base event structure for all ChoirOS events."""
    id: str
    timestamp: int  # Unix ms
    user_id: str
    source: str  # 'user' | 'agent' | 'system'
    event_type: str
    payload: dict

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> bytes:
        return json.dumps(self.to_dict()).encode()

    @classmethod
    def from_json(cls, data: bytes) -> "ChoirEvent":
        d = json.loads(data.decode())
        return cls(**d)


class NATSClient:
    """
    Async NATS JetStream client for event sourcing.

    Usage:
        client = NATSClient()
        await client.connect()
        await client.publish_event(event)
        await client.disconnect()
    """

    def __init__(self, url: str = NATS_URL):
        self.url = url
        self.nc: Optional[nats.NATS] = None
        self.js: Optional[nats.js.JetStreamContext] = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to NATS and initialize JetStream."""
        if self._connected:
            return

        self.nc = await nats.connect(self.url)
        self.js = self.nc.jetstream()
        self._connected = True

        # Ensure streams exist
        await self._ensure_streams()

    async def disconnect(self) -> None:
        """Gracefully disconnect from NATS."""
        if self.nc and self._connected:
            await self.nc.drain()
            self._connected = False

    async def _ensure_streams(self) -> None:
        """Create required streams if they don't exist."""
        streams = [
            StreamConfig(
                name="USER_EVENTS",
                subjects=["choiros.user.>"],
                retention=RetentionPolicy.LIMITS,
                max_age=30 * 24 * 60 * 60 * 1_000_000_000,  # 30 days in nanoseconds
                storage=StorageType.FILE,
            ),
            StreamConfig(
                name="AGENT_EVENTS",
                subjects=["choiros.agent.>"],
                retention=RetentionPolicy.LIMITS,
                max_age=7 * 24 * 60 * 60 * 1_000_000_000,  # 7 days
                storage=StorageType.FILE,
            ),
            StreamConfig(
                name="SYSTEM_EVENTS",
                subjects=["choiros.system.>"],
                retention=RetentionPolicy.LIMITS,
                max_age=24 * 60 * 60 * 1_000_000_000,  # 1 day
                storage=StorageType.MEMORY,
            ),
        ]

        for config in streams:
            try:
                await self.js.add_stream(config)
            except nats.js.errors.BadRequestError:
                # Stream already exists, update it
                await self.js.update_stream(config)

    async def publish_event(self, event: ChoirEvent) -> int:
        """
        Publish an event to the appropriate stream.

        Returns the stream sequence number.
        """
        if not self._connected:
            raise RuntimeError("NATS not connected")

        # Determine subject from event type
        subject = self._event_to_subject(event)

        # Publish and get ack with sequence number
        ack = await self.js.publish(subject, event.to_json())
        return ack.seq

    def _event_to_subject(self, event: ChoirEvent) -> str:
        """Map event to NATS subject hierarchy."""
        base = f"choiros.{event.source}.{event.user_id}"

        # Map event types to subject suffixes
        type_map = {
            "FILE_WRITE": "file.write",
            "FILE_DELETE": "file.delete",
            "FILE_MOVE": "file.move",
            "CONVERSATION_MESSAGE": "message",
            "TOOL_CALL": "tool",
            "TOOL_RESULT": "tool.result",
            "WINDOW_OPEN": "window.open",
            "WINDOW_CLOSE": "window.close",
            "CHECKPOINT": "checkpoint",
            "UNDO": "undo",
        }

        suffix = type_map.get(event.event_type, event.event_type.lower())
        return f"{base}.{suffix}"

    async def get_events(
        self,
        stream: str,
        subject_filter: str = ">",
        start_seq: int = 1,
        limit: int = 1000,
    ) -> list[ChoirEvent]:
        """
        Fetch events from a stream.

        Args:
            stream: Stream name (e.g., "USER_EVENTS")
            subject_filter: Subject pattern to filter
            start_seq: Starting sequence number
            limit: Maximum events to return
        """
        if not self._connected:
            raise RuntimeError("NATS not connected")

        events = []

        # Create ephemeral consumer for fetching
        consumer = await self.js.pull_subscribe(
            subject_filter,
            durable=None,
            stream=stream,
            config=ConsumerConfig(
                deliver_policy="by_start_sequence",
                opt_start_seq=start_seq,
            ),
        )

        try:
            msgs = await consumer.fetch(limit, timeout=5)
            for msg in msgs:
                event = ChoirEvent.from_json(msg.data)
                events.append(event)
                await msg.ack()
        except nats.errors.TimeoutError:
            pass  # No more messages

        return events

    async def subscribe(
        self,
        subject: str,
        callback: Callable[[ChoirEvent], None],
        durable: Optional[str] = None,
    ) -> None:
        """
        Subscribe to events with a callback.

        Args:
            subject: Subject pattern to subscribe to
            callback: Async function to call for each event
            durable: Durable consumer name (for resumable subscriptions)
        """
        if not self._connected:
            raise RuntimeError("NATS not connected")

        async def message_handler(msg):
            event = ChoirEvent.from_json(msg.data)
            await callback(event)
            await msg.ack()

        # Determine stream from subject
        if subject.startswith("choiros.user"):
            stream = "USER_EVENTS"
        elif subject.startswith("choiros.agent"):
            stream = "AGENT_EVENTS"
        else:
            stream = "SYSTEM_EVENTS"

        await self.js.subscribe(
            subject,
            cb=message_handler,
            stream=stream,
            durable=durable,
            manual_ack=True,
        )


# Singleton instance
_client: Optional[NATSClient] = None


async def get_nats_client() -> NATSClient:
    """Get the global NATS client instance."""
    global _client
    if _client is None:
        _client = NATSClient()
        await _client.connect()
    return _client


async def close_nats_client() -> None:
    """Close the global NATS client."""
    global _client
    if _client is not None:
        await _client.disconnect()
        _client = None
