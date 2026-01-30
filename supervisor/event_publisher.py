"""NATS event publisher for ChoirOS."""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import datetime
from typing import Any, Optional

from shared.tenancy import get_default_user_id

from .event_contract import normalize_event_type
from .nats_client import ChoirEvent, NATSClient, get_nats_client

DEFAULT_USER_ID = get_default_user_id()


class EventPublisher:
    def __init__(
        self,
        user_id: str = DEFAULT_USER_ID,
        nats_client: Optional[NATSClient] = None,
    ) -> None:
        self.user_id = user_id
        self._nats: Optional[NATSClient] = nats_client
        self._nats_override: Optional[NATSClient] = nats_client

    async def _get_nats(self) -> NATSClient:
        if self._nats_override is not None:
            return self._nats_override
        if self._nats is None:
            self._nats = await get_nats_client()
        return self._nats

    async def publish(self, event_type: str, payload: dict, source: str = "system") -> int:
        normalized_type = normalize_event_type(event_type)
        event = ChoirEvent(
            id=str(uuid.uuid4()),
            timestamp=int(datetime.now().timestamp() * 1000),
            user_id=self.user_id,
            source=source,
            event_type=normalized_type,
            payload=payload,
        )
        nats = await self._get_nats()
        return await nats.publish_event(event)

    async def publish_event(self, event: ChoirEvent) -> int:
        nats = await self._get_nats()
        return await nats.publish_event(event)

    def publish_sync(self, event_type: str, payload: dict, source: str = "system") -> int:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.publish(event_type, payload, source))
        raise RuntimeError("publish_sync called inside a running event loop; use await publish().")

    async def log_file_write_async(self, path: str, content: bytes, run_id: Optional[str] = None) -> int:
        payload: dict[str, Any] = {
            "path": path,
            "content_hash": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content),
        }
        if run_id:
            payload["run_id"] = run_id
        return await self.publish("file.write", payload, source="agent")

    async def log_file_delete_async(self, path: str, run_id: Optional[str] = None) -> int:
        payload: dict[str, Any] = {"path": path}
        if run_id:
            payload["run_id"] = run_id
        return await self.publish("file.delete", payload, source="agent")

    async def add_message_async(
        self,
        conversation_id: int,
        role: str,
        content: str,
        run_id: Optional[str] = None,
    ) -> int:
        payload: dict[str, Any] = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
        }
        if run_id:
            payload["run_id"] = run_id
        source = "user" if role == "user" else "agent"
        return await self.publish("message", payload, source=source)

    async def log_tool_call_async(
        self,
        conversation_id: int,
        tool_name: str,
        tool_input: dict,
        tool_call_id: str,
        run_id: Optional[str] = None,
    ) -> int:
        payload: dict[str, Any] = {
            "conversation_id": conversation_id,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_call_id": tool_call_id,
        }
        if run_id:
            payload["run_id"] = run_id
        return await self.publish("tool.call", payload, source="agent")

    async def log_tool_result_async(
        self,
        conversation_id: int,
        tool_name: str,
        tool_result: Any,
        tool_call_id: str,
        run_id: Optional[str] = None,
    ) -> int:
        payload: dict[str, Any] = {
            "conversation_id": conversation_id,
            "tool_name": tool_name,
            "tool_result": tool_result,
            "tool_call_id": tool_call_id,
        }
        if run_id:
            payload["run_id"] = run_id
        return await self.publish("tool.result", payload, source="agent")


_publisher: Optional[EventPublisher] = None
_publishers_by_user: dict[str, EventPublisher] = {}


def get_publisher(user_id: Optional[str] = None) -> EventPublisher:
    global _publisher, _publishers_by_user
    if user_id is None:
        if _publisher is None:
            _publisher = EventPublisher()
        return _publisher
    if user_id not in _publishers_by_user:
        _publishers_by_user[user_id] = EventPublisher(user_id=user_id)
    return _publishers_by_user[user_id]
