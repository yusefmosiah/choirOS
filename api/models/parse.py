"""Pydantic models for parsing requests/responses."""

from pydantic import BaseModel
from typing import Optional


class ParseUrlRequest(BaseModel):
    """Request to parse a URL."""
    url: str


class ParseUploadResponse(BaseModel):
    """Response after parsing upload or URL."""
    artifact_id: str
    path: str
    name: str
    mime_type: str
    source_type: str  # "youtube", "web", "upload"
    content_preview: str  # First 200 chars


class ParseError(BaseModel):
    """Error response for parsing failures."""
    error: str
    detail: Optional[str] = None
