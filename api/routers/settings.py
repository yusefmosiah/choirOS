"""Settings router - user settings and provider configuration."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
import time

router = APIRouter()


class ProviderConfig(BaseModel):
    provider: Literal["bedrock", "zai"]
    model: str
    status: str = "active"


class ProviderRequest(BaseModel):
    provider: Literal["bedrock", "zai"]


class ProviderTestResult(BaseModel):
    provider: str
    valid: bool
    latency_ms: Optional[int] = None
    model: str
    error: Optional[str] = None


@router.get("/provider", response_model=ProviderConfig)
async def get_provider():
    """
    Get the current LLM provider configuration.

    Returns:
        ProviderConfig with current provider, model, and status
    """
    from supervisor.db import get_store
    from supervisor.baml_client.provider_factory import get_provider_factory

    db = get_store()
    factory = get_provider_factory(db)

    provider = factory.get_provider()
    config = factory.get_provider_config()

    return ProviderConfig(
        provider=provider,
        model=config.get("model", "unknown"),
        status="active",
    )


@router.post("/provider", response_model=ProviderConfig)
async def set_provider(request: ProviderRequest):
    """
    Set the LLM provider.

    Args:
        request: ProviderRequest with provider name

    Returns:
        Updated ProviderConfig

    Raises:
        HTTPException: If provider is invalid
    """
    from supervisor.db import get_store
    from supervisor.baml_client.provider_factory import get_provider_factory

    db = get_store()
    factory = get_provider_factory(db)

    try:
        factory.set_provider(request.provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Emit a provider.changed event
    await db.append_async(
        "provider.changed",
        {"provider": request.provider, "model": factory.get_provider_config()["model"]},
        source="user",
    )

    provider = factory.get_provider()
    config = factory.get_provider_config()

    return ProviderConfig(
        provider=provider,
        model=config.get("model", "unknown"),
        status="active",
    )


@router.post("/provider/test", response_model=ProviderTestResult)
async def test_provider(request: ProviderRequest):
    """
    Test the connection to a provider.

    Args:
        request: ProviderRequest with provider name to test

    Returns:
        ProviderTestResult with validity, latency, and model info
    """
    from supervisor.db import get_store
    from supervisor.baml_client.provider_factory import get_provider_factory

    db = get_store()
    factory = get_provider_factory(db)

    result = factory.test_connection(request.provider)

    # Emit a provider.test event
    await db.append_async(
        "provider.test",
        {
            "provider": request.provider,
            "valid": result["valid"],
            "latency_ms": result.get("latency_ms"),
        },
        source="user",
    )

    return ProviderTestResult(**result)
