"""Pydantic models for artifacts."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Artifact(BaseModel):
    """An artifact (parsed source file)."""
    id: str
    path: str
    name: str
    mime_type: str
    content: str
    source_url: Optional[str] = None
    source_type: str  # "youtube", "web", "upload"
    created_at: datetime
    metadata: dict = {}


class ArtifactCreate(BaseModel):
    """Request to create an artifact directly."""
    path: str
    name: str
    content: str
    mime_type: str = "text/markdown"
    source_url: Optional[str] = None
    source_type: str = "manual"


class ArtifactResponse(BaseModel):
    """Response after creating/fetching an artifact."""
    id: str
    path: str
    name: str
    mime_type: str
    source_url: Optional[str] = None
    source_type: str
    created_at: datetime
    content_preview: str  # First 200 chars


class ArtifactListResponse(BaseModel):
    """Response for listing artifacts."""
    artifacts: list[ArtifactResponse]
    total: int
