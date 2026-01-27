from __future__ import annotations

import json
from collections import deque
from typing import Any, Deque, Optional

from .db import EventStore


def _tool_key(tool_name: str, tool_input: dict) -> str:
    encoded = json.dumps(tool_input or {}, sort_keys=True, separators=(",", ":"))
    return f"{tool_name}:{encoded}"


class ReplayToolCache:
    def __init__(self, tool_calls: list[dict]) -> None:
        self._by_key: dict[str, Deque[Any]] = {}
        for call in tool_calls:
            key = _tool_key(call["tool_name"], call.get("tool_input") or {})
            self._by_key.setdefault(key, deque()).append(call.get("tool_result"))

    @classmethod
    def from_store(cls, store: EventStore, conversation_id: int) -> "ReplayToolCache":
        tool_calls = store.list_tool_calls(conversation_id)
        return cls(tool_calls)

    def get(self, tool_name: str, tool_input: dict) -> Optional[Any]:
        key = _tool_key(tool_name, tool_input or {})
        queue = self._by_key.get(key)
        if not queue:
            return None
        return queue.popleft()
