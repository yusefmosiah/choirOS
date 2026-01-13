"""OpenAI adapter implementing the unified LLM interface."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from openai import OpenAI

from .base import ContentBlock, LLMResponse, Message, ToolCall


def _convert_tool_definition(tool: Dict[str, Any]) -> Dict[str, Any]:
    """Convert generic tool definition into OpenAI function tool."""
    return {
        "type": "function",
        "function": {
            "name": tool.get("name"),
            "description": tool.get("description"),
            "parameters": tool.get("input_schema", {}),
        },
    }


def _convert_content_block(block: ContentBlock) -> List[Dict[str, Any]]:
    """Convert a content block into OpenAI message records."""
    block_type = block["type"]
    if block_type == "text":  # type: ignore[index]
        return [{"role": "assistant", "content": block["text"]}]  # type: ignore[index]
    if block_type == "tool_use":  # type: ignore[index]
        return [{
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": block["id"],  # type: ignore[index]
                "type": "function",
                "function": {
                    "name": block["name"],  # type: ignore[index]
                    "arguments": json.dumps(block.get("input", {})),  # type: ignore[index]
                }
            }]
        }]
    if block_type == "tool_result":  # type: ignore[index]
        return [{
            "role": "tool",
            "tool_call_id": block["tool_use_id"],  # type: ignore[index]
            "content": block.get("content", ""),  # type: ignore[index]
        }]
    raise ValueError(f"Unsupported block type: {block_type}")


class OpenAIClient:
    """Adapter for OpenAI chat completions API."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = OpenAI(api_key=api_key)

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
        openai_messages: List[Dict[str, Any]] = []
        for message in messages:
            content = message.get("content", "")
            if isinstance(content, list):
                for block in content:
                    openai_messages.extend(_convert_content_block(block))
            else:
                openai_messages.append({"role": message["role"], "content": content})

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": openai_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }

        if tools:
            kwargs["tools"] = [_convert_tool_definition(t) for t in tools]
        if extra:
            kwargs.update(extra)

        resp = self.client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        message = choice.message

        tool_calls: List[ToolCall] = []
        for call in message.tool_calls or []:
            name = getattr(call.function, "name", "")
            arguments_raw = getattr(call.function, "arguments", "{}")
            try:
                arguments = json.loads(arguments_raw)
            except json.JSONDecodeError:
                arguments = {"_raw": arguments_raw}
            tool_calls.append({"id": call.id, "name": name, "arguments": arguments})

        return {
            "content": message.content or "",
            "tool_calls": tool_calls,
            "stop_reason": choice.finish_reason,
        }
