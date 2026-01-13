"""Factory helpers to build LLM clients from configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .anthropic_client import AnthropicClient
from .bedrock_client import BedrockConverseClient
from .google_client import GoogleClient
from .openai_client import OpenAIClient


@dataclass
class LLMSettings:
    provider: str
    model: str
    anthropic_api_key: str | None = None
    aws_region: str = "us-east-1"
    openai_api_key: str | None = None
    google_api_key: str | None = None
    google_model: str | None = None

    @classmethod
    def from_env(cls) -> "LLMSettings":
        return cls(
            provider=os.environ.get("LLM_PROVIDER", "bedrock"),
            model=os.environ.get("LLM_MODEL", "us.anthropic.claude-opus-4-5-20251101-v1:0"),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            aws_region=os.environ.get("AWS_REGION", "us-east-1"),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            google_api_key=os.environ.get("GOOGLE_API_KEY"),
            google_model=os.environ.get("GOOGLE_MODEL"),
        )


def build_llm_client(settings: LLMSettings):
    """Instantiate an LLM client based on provider settings."""
    provider = settings.provider.lower()
    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for the Anthropic provider")
        return AnthropicClient(api_key=settings.anthropic_api_key)
    if provider in {"bedrock", "bedrock-anthropic", "aws-bedrock"}:
        return BedrockConverseClient(region=settings.aws_region)
    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for the OpenAI provider")
        return OpenAIClient(api_key=settings.openai_api_key)
    if provider == "google":
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required for the Google provider")
        model = settings.google_model or settings.model
        return GoogleClient(api_key=settings.google_api_key or "", default_model=model)
    raise ValueError(f"Unknown LLM provider: {settings.provider}")
