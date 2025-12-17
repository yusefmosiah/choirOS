"""Artifacts router - CRUD for artifacts."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from api.models.artifact import ArtifactResponse, ArtifactListResponse
from api.services.artifact_store import (
    get_artifact,
    list_artifacts,
    delete_artifact,
    create_artifact,
    to_response,
)


class CreateArtifactRequest(BaseModel):
    name: str
    content: str
    source_type: str = "agent"
    mime_type: str = "text/markdown"


router = APIRouter()


@router.post("")
async def create_new_artifact(request: CreateArtifactRequest):
    """Create a new artifact (used for saving agent responses)."""
    artifact = create_artifact(
        name=request.name,
        content=request.content,
        source_type=request.source_type,
        mime_type=request.mime_type,
    )
    return {
        "artifact_id": artifact.id,
        "name": artifact.name,
        "path": artifact.path,
    }


@router.get("", response_model=ArtifactListResponse)
async def list_all_artifacts():
    """List all artifacts (newest first)."""
    artifacts = list_artifacts()
    return ArtifactListResponse(
        artifacts=[to_response(a) for a in artifacts],
        total=len(artifacts),
    )


@router.get("/{artifact_id}")
async def get_artifact_by_id(artifact_id: str, include_content: bool = True):
    """
    Get an artifact by ID.

    If include_content is False, only returns metadata.
    """
    artifact = get_artifact(artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    if include_content:
        return artifact
    else:
        return to_response(artifact)


@router.delete("/{artifact_id}")
async def delete_artifact_by_id(artifact_id: str):
    """Delete an artifact by ID."""
    success = delete_artifact(artifact_id)

    if not success:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return {"deleted": True, "id": artifact_id}
