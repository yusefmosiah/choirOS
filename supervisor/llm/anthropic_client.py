"""Anthropic SDK adapter implementing the unified LLM interface."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import anthropic

from .base import ContentBlock, LLMClient, LLMResponse, Message, ToolCall


def _convert_content(content: ContentBlock) -> Dict[str, Any]:
    """Pass through Anthropic-compatible content blocks."""
    return dict(content)


class AnthropicClient:
    """Wraps the Anthropic SDK to satisfy the LLMClient protocol."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=api_key)

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
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        system = "\n".join(system_parts) if system_parts else None
        non_system = [m for m in messages if m["role"] != "system"]

        anthropic_messages: List[Dict[str, Any]] = []
        for message in non_system:
            converted: Dict[str, Any] = {"role": message["role"]}
            content = message.get("content", "")
            if isinstance(content, list):
                converted["content"] = [_convert_content(block) for block in content]
            else:
                converted["content"] = content
            anthropic_messages.append(converted)

        kwargs: Dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "messages": anthropic_messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools
        if extra:
            kwargs.update(extra)

        resp = self.client.messages.create(**kwargs)

        text_chunks: List[str] = []
        tool_calls: List[ToolCall] = []
        for block in resp.content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                text_chunks.append(block.text)
            elif block_type == "tool_use":
                tool_calls.append({
                    "id": getattr(block, "id", None),
                    "name": getattr(block, "name", ""),
                    "arguments": getattr(block, "input", {}),
                })

        return {
            "content": "".join(text_chunks),
            "tool_calls": tool_calls,
            "stop_reason": getattr(resp, "stop_reason", None),
        }
