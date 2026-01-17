"""
Canonical event contract for ChoirOS.

Keep this file in sync with docs/specs/CHOIR_EVENT_CONTRACT_SPEC.md.
"""

from typing import Literal

CHOIR_STREAM = "CHOIR"
CHOIR_SUBJECT_ROOT = "choiros"
CHOIR_SUBJECT_PATTERN = "choiros.>"
CHOIR_SUBJECT_FORMAT = "choiros.{user_id}.{source}.{event_type}"

EventSource = Literal["user", "agent", "system"]

# Canonical v0 event types (dot-delimited, lower-case)
CHOIR_EVENT_TYPES_V0 = (
    "file.write",
    "file.delete",
    "file.move",
    "message",
    "tool.call",
    "tool.result",
    "window.open",
    "window.close",
    "checkpoint",
    "undo",
)

_LEGACY_EVENT_TYPE_MAP = {
    "FILE_WRITE": "file.write",
    "FILE_DELETE": "file.delete",
    "FILE_MOVE": "file.move",
    "CONVERSATION_MESSAGE": "message",
    "TOOL_CALL": "tool.call",
    "TOOL_RESULT": "tool.result",
    "WINDOW_OPEN": "window.open",
    "WINDOW_CLOSE": "window.close",
    "CHECKPOINT": "checkpoint",
    "UNDO": "undo",
}


def build_subject(user_id: str, source: EventSource, event_type: str) -> str:
    return f"{CHOIR_SUBJECT_ROOT}.{user_id}.{source}.{event_type}"


def normalize_event_type(event_type: str) -> str:
    raw = (event_type or "").strip()
    if not raw:
        return raw
    upper = raw.upper()
    if upper in _LEGACY_EVENT_TYPE_MAP:
        return _LEGACY_EVENT_TYPE_MAP[upper]
    return raw.lower().replace("_", ".")
