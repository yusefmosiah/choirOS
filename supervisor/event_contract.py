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
    # Core events
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
    # Notes (AHDB-typed telemetry)
    "note.observation",
    "note.hypothesis",
    "note.hyperthesis",
    "note.conjecture",
    "note.status",
    "note.request.help",
    "note.request.verify",
    # Receipts (capabilities + verification)
    "receipt.read",
    "receipt.patch",
    "receipt.verifier",
    "receipt.net",
    "receipt.db",
    "receipt.export",
    "receipt.publish",
    "receipt.context.footprint",
    "receipt.verifier.results",
    "receipt.verifier.attestations",
    "receipt.discrepancy.report",
    "receipt.commit",
    "receipt.ahdb.delta",
    "receipt.evidence.set.hash",
    "receipt.retrieval",
    "receipt.conjecture.set",
    "receipt.policy.decision.tokens",
    "receipt.security.attestations",
    "receipt.hyperthesis.delta",
    "receipt.expansion.plan",
    "receipt.projection.rebuild",
    "receipt.attack.report",
    "receipt.disclosure.objects",
    "receipt.mitigation.proposals",
    "receipt.preference.decision",
    "receipt.timeout",
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


def _normalize_segments(value: str) -> str:
    return value.strip().lower().replace("/", ".").replace("_", ".")


def build_subject(user_id: str, source: EventSource, event_type: str) -> str:
    return f"{CHOIR_SUBJECT_ROOT}.{user_id}.{source}.{event_type}"


def normalize_event_type(event_type: str) -> str:
    raw = (event_type or "").strip()
    if not raw:
        return raw
    upper = raw.upper()
    if upper in _LEGACY_EVENT_TYPE_MAP:
        return _LEGACY_EVENT_TYPE_MAP[upper]
    if upper.startswith("RECEIPT/"):
        suffix = raw.split("/", 1)[1]
        return f"receipt.{_normalize_segments(suffix)}"
    if upper.endswith("_RECEIPT") and upper != "RECEIPT":
        suffix = raw[: -len("_RECEIPT")]
        return f"receipt.{_normalize_segments(suffix)}"
    return _normalize_segments(raw)
