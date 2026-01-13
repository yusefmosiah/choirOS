"""AWS Bedrock Converse adapter implementing the unified LLM interface."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import boto3

from .base import ContentBlock, LLMResponse, Message, ToolCall


def _convert_tool_definition(tool: Dict[str, Any]) -> Dict[str, Any]:
    """Convert generic tool definition to Bedrock Converse format."""
    return {
        "toolSpec": {
            "name": tool.get("name"),
            "description": tool.get("description"),
            "inputSchema": {"json": tool.get("input_schema", {})},
        }
    }


def _convert_content_block(block: ContentBlock) -> Dict[str, Any]:
    """Convert ContentBlock to Bedrock Converse content shape."""
    block_type = block["type"]
    if block_type == "text":  # type: ignore[index]
        return {"text": block["text"]}  # type: ignore[index]
    if block_type == "tool_use":  # type: ignore[index]
        return {
            "toolUse": {
                "toolUseId": block["id"],  # type: ignore[index]
                "name": block["name"],  # type: ignore[index]
                "input": block.get("input", {}),  # type: ignore[index]
            }
        }
    if block_type == "tool_result":  # type: ignore[index]
        content = block.get("content", "")  # type: ignore[index]
        content_list = content if isinstance(content, list) else [{"text": str(content)}]
        return {
            "toolResult": {
                "toolUseId": block["tool_use_id"],  # type: ignore[index]
                "status": block.get("status") or "success",  # type: ignore[index]
                "content": [
                    {"text": c["text"]} if isinstance(c, dict) and "text" in c else {"text": str(c)}
                    for c in content_list
                ],
            }
        }
    raise ValueError(f"Unsupported content block type: {block_type}")


class BedrockConverseClient:
    """Adapter for AWS Bedrock Converse API."""

    def __init__(self, region: str = "us-east-1"):
        self.client = boto3.client("bedrock-runtime", region_name=region)

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
        bedrock_messages: List[Dict[str, Any]] = []
        for message in messages:
            content = message.get("content", "")
            if isinstance(content, list):
                converted_content = [_convert_content_block(block) for block in content]
            else:
                converted_content = [{"text": str(content)}]
            bedrock_messages.append({"role": message["role"], "content": converted_content})

        kwargs: Dict[str, Any] = {
            "modelId": model,
            "messages": bedrock_messages,
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": temperature,
                "topP": top_p,
            },
        }

        if tools:
            kwargs["toolConfig"] = {"tools": [_convert_tool_definition(t) for t in tools]}
        if extra:
            kwargs.update(extra)

        resp = self.client.converse(**kwargs)

        content_blocks = resp["output"]["message"]["content"]
        text_chunks: List[str] = []
        tool_calls: List[ToolCall] = []
        for block in content_blocks:
            if "text" in block:
                text_chunks.append(block["text"])
            elif "toolUse" in block:
                tool_use = block["toolUse"]
                tool_calls.append({
                    "id": tool_use.get("toolUseId"),
                    "name": tool_use.get("name", ""),
                    "arguments": tool_use.get("input", {}),
                })

        return {
            "content": "".join(text_chunks),
            "tool_calls": tool_calls,
            "stop_reason": resp.get("stopReason"),
        }
