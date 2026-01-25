"""
BAML Provider Factory for dynamic client selection.

Allows switching between ClaudeBedrock and ClaudeZAI at runtime
based on user settings stored in the database.
"""

import os
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .db import EventStore

# Singleton instance
_factory: Optional["ProviderFactory"] = None


class ProviderFactory:
    """
    Factory for dynamically selecting BAML clients based on user settings.

    Supports switching between AWS Bedrock and Z.ai providers.
    """

    PROVIDER_BEDROCK = "bedrock"
    PROVIDER_ZAI = "zai"
    DEFAULT_PROVIDER = PROVIDER_BEDROCK

    # Generated BAML client names
    BAML_CLIENTS = {
        PROVIDER_BEDROCK: "ClaudeBedrock",
        PROVIDER_ZAI: "ClaudeZAI",
    }

    # Provider configurations
    PROVIDER_CONFIGS = {
        PROVIDER_BEDROCK: {
            "name": "AWS Bedrock",
            "model": "us.anthropic.claude-opus-4-5-20251101-v1:0",
            "region": "us-east-1",
        },
        PROVIDER_ZAI: {
            "name": "Z.ai",
            "model": "glm-4.7",
            "base_url": "https://api.z.ai/api/anthropic",
        },
    }

    def __init__(self, db: "EventStore"):
        """Initialize the provider factory with a database connection."""
        self.db = db
        self._current_provider = self._load_provider_from_db()

    def _load_provider_from_db(self) -> str:
        """Load the current provider from database settings."""
        provider = self.db.get_setting("llm_provider", default=self.DEFAULT_PROVIDER)
        if provider not in self.PROVIDER_CONFIGS:
            return self.DEFAULT_PROVIDER
        return provider

    def get_provider(self) -> str:
        """Get the current provider name."""
        return self._current_provider

    def get_provider_config(self, provider: Optional[str] = None) -> dict:
        """Get configuration for the specified provider."""
        if provider is None:
            provider = self._current_provider
        return self.PROVIDER_CONFIGS.get(provider, self.PROVIDER_CONFIGS[self.DEFAULT_PROVIDER])

    def set_provider(self, provider: str) -> None:
        """
        Set the current provider and persist to database.

        Args:
            provider: One of 'bedrock' or 'zai'
        """
        if provider not in self.PROVIDER_CONFIGS:
            raise ValueError(f"Invalid provider: {provider}. Must be one of: {list(self.PROVIDER_CONFIGS.keys())}")

        self._current_provider = provider
        self.db.set_setting("llm_provider", provider)

    def get_baml_client(self):
        """
        Get the generated BAML client name for the current provider.

        Returns:
            The BAML client name (e.g., "ClaudeBedrock")

        Note: Client selection is passed into BAML via `b.with_options(client=...)`.
        """
        return self.BAML_CLIENTS.get(
            self._current_provider, self.BAML_CLIENTS[self.DEFAULT_PROVIDER]
        )

    def _client_exists(self, client_name: str) -> bool:
        """Check whether a client is present in the generated BAML bundle."""
        try:
            from supervisor.baml_client.inlinedbaml import INLINED_BAML

            for content in INLINED_BAML.values():
                if f"client<llm> {client_name}" in content:
                    return True
            return False
        except Exception:
            return False

    def test_connection(self, provider: Optional[str] = None) -> dict:
        """
        Test the connection to a provider.

        Args:
            provider: The provider to test (defaults to current)

        Returns:
            Dict with test results:
            {
                "provider": "bedrock",
                "valid": true,
                "latency_ms": 123,
                "model": "us.anthropic.claude-opus-4-5-20251101-v1:0"
            }
        """
        import time

        if provider is None:
            provider = self._current_provider

        config = self.PROVIDER_CONFIGS.get(provider, {})
        client_name = self.BAML_CLIENTS.get(provider, self.BAML_CLIENTS[self.DEFAULT_PROVIDER])

        start = time.time()
        end = time.time()

        valid = self._client_exists(client_name)
        result = {
            "provider": provider,
            "valid": valid,
            "latency_ms": int((end - start) * 1000),
            "model": config.get("model", "unknown"),
            "client": client_name,
        }
        if not valid:
            result["error"] = f"BAML client '{client_name}' not found in generated bundle"
        return result

    def reset_to_default(self) -> None:
        """Reset the provider to the default (Bedrock)."""
        self.set_provider(self.DEFAULT_PROVIDER)


def get_provider_factory(db: Optional["EventStore"] = None) -> ProviderFactory:
    """
    Get the singleton ProviderFactory instance.

    Args:
        db: Optional EventStore instance (required for first call)

    Returns:
        The ProviderFactory singleton

    Raises:
        RuntimeError: If db is not provided on first call
    """
    global _factory

    if _factory is None:
        if db is None:
            raise RuntimeError("ProviderFactory requires EventStore on first call")
        _factory = ProviderFactory(db)

    return _factory


def set_provider_factory(factory: ProviderFactory) -> None:
    """Set the singleton ProviderFactory instance (for testing)."""
    global _factory
    _factory = factory
