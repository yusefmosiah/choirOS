"""Google (Gemini) adapter implementing the unified LLM interface."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import google.generativeai as genai

from .base import LLMResponse, Message


class GoogleClient:
    """Adapter for the Gemini Python SDK."""

    def __init__(self, api_key: str, default_model: str = "gemini-1.5-pro"):
        genai.configure(api_key=api_key)
        self.default_model = default_model

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
        model_name = model or self.default_model

        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        system_instruction = "\n".join(system_parts) if system_parts else None
        conversation = [m for m in messages if m["role"] != "system"]

        gen_model = genai.GenerativeModel(
            model_name,
            system_instruction=system_instruction,
        )

        gen_messages: List[Dict[str, Any]] = []
        for message in conversation:
            content = message.get("content", "")
            if isinstance(content, list):
                text_parts = [block.get("text", "") for block in content if block.get("type") == "text"]
                content = "\n".join(text_parts)
            gen_messages.append({"role": message["role"], "parts": [content]})

        config: Dict[str, Any] = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }
        if extra:
            config.update(extra)

        resp = gen_model.generate_content(
            gen_messages,
            generation_config=config,
        )

        return {
            "content": resp.text or "",
            "tool_calls": [],
            "stop_reason": getattr(resp, "finish_reason", None),
        }
