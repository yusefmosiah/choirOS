"""Parse router - URL and file parsing endpoints."""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from urllib.parse import urlparse
from typing import Optional
from pydantic import BaseModel

from models.parse import ParseUrlRequest, ParseUploadResponse, ParseError
from services.artifact_store import (
    create_artifact,
    find_by_source_url,
    update_artifact,
    generate_unique_name,
    to_response,
)
from services.youtube_parser import parse_youtube, is_youtube_url
from services.web_parser import parse_web_page
from services.document_parser import parse_document, get_supported_extensions

router = APIRouter()


class CheckUrlResponse(BaseModel):
    exists: bool
    artifact_id: Optional[str] = None
    name: Optional[str] = None


class ParseUrlRequestWithMode(BaseModel):
    url: str
    mode: str = "create"  # "create", "overwrite", "keep_both"


@router.post("/check-url", response_model=CheckUrlResponse)
async def check_url(request: ParseUrlRequest):
    """
    Check if a URL has already been parsed.
    Returns existing artifact info if found.
    """
    url = request.url.strip()
    existing = find_by_source_url(url)

    if existing:
        return CheckUrlResponse(
            exists=True,
            artifact_id=existing.id,
            name=existing.name,
        )

    return CheckUrlResponse(exists=False)


@router.post("/url", response_model=ParseUploadResponse)
async def parse_url(request: ParseUrlRequestWithMode):
    """
    Parse a URL and create an artifact.

    Modes:
    - create: Normal create (fails if duplicate check not done)
    - overwrite: Replace existing artifact with same URL
    - keep_both: Create new artifact with incremented name

    Supports:
    - YouTube URLs (extracts transcript)
    - Web pages (extracts article content)
    """
    url = request.url.strip()
    mode = request.mode

    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    # Validate URL
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid URL format")

    # Check for existing artifact
    existing = find_by_source_url(url)

    if existing and mode == "create":
        # Return conflict - client should have checked first
        raise HTTPException(
            status_code=409,
            detail={
                "error": "duplicate",
                "artifact_id": existing.id,
                "name": existing.name,
            }
        )

    try:
        # Route to appropriate parser
        if is_youtube_url(url):
            result = parse_youtube(url)
            source_type = "youtube"
        else:
            result = parse_web_page(url)
            source_type = "web"

        if existing and mode == "overwrite":
            # Update existing artifact
            artifact = update_artifact(
                existing.id,
                name=result["filename"],
                content=result["content"],
                metadata=result.get("metadata", {}),
            )
        else:
            # Create new artifact
            filename = result["filename"]
            if mode == "keep_both" and existing:
                filename = generate_unique_name(filename)

            artifact = create_artifact(
                name=filename,
                content=result["content"],
                source_type=source_type,
                source_url=url,
                metadata=result.get("metadata", {}),
            )

        return ParseUploadResponse(
            artifact_id=artifact.id,
            path=artifact.path,
            name=artifact.name,
            mime_type=artifact.mime_type,
            source_type=source_type,
            content_preview=artifact.content[:200] if artifact.content else "",
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parse error: {str(e)}")


@router.post("/upload", response_model=ParseUploadResponse)
async def parse_upload(file: UploadFile = File(...)):
    """
    Parse an uploaded file and create an artifact.

    Supports: PDF, DOCX, PPTX, XLSX, images, audio, and more.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Check extension
    extension = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    supported = get_supported_extensions()

    if extension not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {extension}. Supported: {', '.join(supported)}"
        )

    try:
        # Read file content
        content = await file.read()

        # Parse document
        result = parse_document(content, file.filename)

        # Create artifact with unique name
        filename = generate_unique_name(result["filename"])

        artifact = create_artifact(
            name=filename,
            content=result["content"],
            source_type="upload",
            metadata=result.get("metadata", {}),
        )

        return ParseUploadResponse(
            artifact_id=artifact.id,
            path=artifact.path,
            name=artifact.name,
            mime_type=artifact.mime_type,
            source_type="upload",
            content_preview=artifact.content[:200] if artifact.content else "",
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parse error: {str(e)}")


@router.get("/supported-types")
async def get_supported_types():
    """Get list of supported file types for upload."""
    return {
        "extensions": get_supported_extensions(),
        "url_types": ["youtube", "web"],
    }
