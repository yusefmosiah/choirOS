"""In-memory artifact store."""

from datetime import datetime
from typing import Optional
import uuid
import re

from api.models.artifact import Artifact, ArtifactResponse


# In-memory storage (replaced by SQLite in Phase 3)
_artifacts: dict[str, Artifact] = {}


def create_artifact(
    name: str,
    content: str,
    source_type: str,
    source_url: Optional[str] = None,
    mime_type: str = "text/markdown",
    metadata: dict = {},
) -> Artifact:
    """Create and store a new artifact."""
    artifact_id = str(uuid.uuid4())
    path = f"/sources/{name}"

    artifact = Artifact(
        id=artifact_id,
        path=path,
        name=name,
        mime_type=mime_type,
        content=content,
        source_url=source_url,
        source_type=source_type,
        created_at=datetime.now(),
        metadata=metadata,
    )

    _artifacts[artifact_id] = artifact
    return artifact


def get_artifact(artifact_id: str) -> Optional[Artifact]:
    """Get an artifact by ID."""
    return _artifacts.get(artifact_id)


def find_by_source_url(source_url: str) -> Optional[Artifact]:
    """Find an artifact by its source URL."""
    for artifact in _artifacts.values():
        if artifact.source_url == source_url:
            return artifact
    return None


def find_by_name(name: str) -> Optional[Artifact]:
    """Find an artifact by its name."""
    for artifact in _artifacts.values():
        if artifact.name == name:
            return artifact
    return None


def generate_unique_name(base_name: str) -> str:
    """Generate a unique name by appending a number if needed."""
    # Remove .md extension if present
    if base_name.endswith('.md'):
        stem = base_name[:-3]
        ext = '.md'
    else:
        stem = base_name
        ext = ''

    # Check if base name exists
    if not find_by_name(base_name):
        return base_name

    # Try incrementing numbers
    counter = 2
    while True:
        new_name = f"{stem} ({counter}){ext}"
        if not find_by_name(new_name):
            return new_name
        counter += 1


def update_artifact(
    artifact_id: str,
    name: Optional[str] = None,
    content: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Optional[Artifact]:
    """Update an existing artifact."""
    artifact = _artifacts.get(artifact_id)
    if not artifact:
        return None

    # Create updated artifact (Pydantic models are immutable)
    updated = Artifact(
        id=artifact.id,
        path=f"/sources/{name}" if name else artifact.path,
        name=name if name else artifact.name,
        mime_type=artifact.mime_type,
        content=content if content else artifact.content,
        source_url=artifact.source_url,
        source_type=artifact.source_type,
        created_at=datetime.now(),  # Update timestamp
        metadata=metadata if metadata else artifact.metadata,
    )

    _artifacts[artifact_id] = updated
    return updated


def list_artifacts() -> list[Artifact]:
    """List all artifacts, sorted by creation time (newest first)."""
    return sorted(
        _artifacts.values(),
        key=lambda a: a.created_at,
        reverse=True
    )


def delete_artifact(artifact_id: str) -> bool:
    """Delete an artifact by ID."""
    if artifact_id in _artifacts:
        del _artifacts[artifact_id]
        return True
    return False


def to_response(artifact: Artifact) -> ArtifactResponse:
    """Convert artifact to response model (without full content)."""
    return ArtifactResponse(
        id=artifact.id,
        path=artifact.path,
        name=artifact.name,
        mime_type=artifact.mime_type,
        source_url=artifact.source_url,
        source_type=artifact.source_type,
        created_at=artifact.created_at,
        content_preview=artifact.content[:200] if artifact.content else "",
    )
