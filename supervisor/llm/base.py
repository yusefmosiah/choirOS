"""Shared LLM interfaces and message types."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Protocol, TypedDict, Union

Role = Literal["user", "assistant", "system", "tool"]


class TextBlock(TypedDict):
    type: Literal["text"]
    text: str


class ToolUseBlock(TypedDict):
    type: Literal["tool_use"]
    id: str
    name: str
    input: Dict[str, Any]


class ToolResultBlock(TypedDict):
    type: Literal["tool_result"]
    tool_use_id: str
    content: str
    status: Optional[str]


ContentBlock = Union[TextBlock, ToolUseBlock, ToolResultBlock]
MessageContent = Union[str, List[ContentBlock]]


class Message(TypedDict, total=False):
    role: Role
    content: MessageContent
    name: Optional[str]
    tool_call_id: Optional[str]


class ToolCall(TypedDict, total=False):
    id: Optional[str]
    name: str
    arguments: Dict[str, Any]


class LLMResponse(TypedDict, total=False):
    content: str
    tool_calls: List[ToolCall]
    stop_reason: Optional[str]


class LLMClient(Protocol):
    """Provider-agnostic chat interface."""

    def chat(
        self,
        messages: List[Message],
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        top_p: float = 0.95,
        tools: Optional[List[Dict[str, Any]]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        """
        Synchronously generate a single assistant reply given a conversation.

        - messages: Full conversation history (system/user/assistant/tool).
        - model: Provider-specific model identifier.
        - extra: Optional provider-specific parameters; opaque to agent layer.
        - tools: Optional tool specifications for providers that support tool use.
        """
        ...
