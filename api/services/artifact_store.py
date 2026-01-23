"""Artifact store with file-backed persistence."""

from datetime import datetime
from typing import Optional
import uuid
import re
import os
from pathlib import Path
import json

from api.models.artifact import Artifact, ArtifactResponse


# In-memory cache (file-backed persistence)
_artifacts: dict[str, Artifact] = {}

ROOT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = Path(os.getenv("CHOIR_ARTIFACTS_DIR", ROOT_DIR / "artifacts"))
INDEX_PATH = ARTIFACTS_DIR / "index.json"


def _ensure_storage() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def _load_index() -> list[dict]:
    if not INDEX_PATH.exists():
        return []
    try:
        return json.loads(INDEX_PATH.read_text())
    except Exception:
        return []


def _save_index(records: list[dict]) -> None:
    _ensure_storage()
    INDEX_PATH.write_text(json.dumps(records, indent=2))


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9_-]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "artifact"


def _artifact_path(artifact_id: str, name: str, mime_type: str) -> Path:
    ext = ".md" if mime_type == "text/markdown" else ".txt"
    slug = _slugify(name)
    return ARTIFACTS_DIR / f"{slug}-{artifact_id}{ext}"


def _hydrate_from_index() -> None:
    _ensure_storage()
    records = _load_index()
    for record in records:
        artifact_id = record.get("id")
        path = record.get("path")
        if not artifact_id or not path:
            continue
        file_path = Path(path)
        if not file_path.exists():
            continue
        try:
            content = file_path.read_text()
        except Exception:
            continue
        created_at_raw = record.get("created_at")
        try:
            created_at = datetime.fromisoformat(created_at_raw) if created_at_raw else datetime.now()
        except Exception:
            created_at = datetime.now()
        artifact = Artifact(
            id=artifact_id,
            path=str(file_path),
            name=record.get("name", artifact_id),
            mime_type=record.get("mime_type", "text/markdown"),
            content=content,
            source_url=record.get("source_url"),
            source_type=record.get("source_type", "agent"),
            created_at=created_at,
            metadata=record.get("metadata", {}),
        )
        _artifacts[artifact_id] = artifact


_hydrate_from_index()


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
    _ensure_storage()
    file_path = _artifact_path(artifact_id, name, mime_type)
    file_path.write_text(content)
    path = str(file_path)

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
    records = _load_index()
    records.append({
        "id": artifact.id,
        "path": artifact.path,
        "name": artifact.name,
        "mime_type": artifact.mime_type,
        "source_url": artifact.source_url,
        "source_type": artifact.source_type,
        "created_at": artifact.created_at.isoformat(),
        "metadata": artifact.metadata,
    })
    _save_index(records)
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
    if base_name.endswith('.md'):
        stem = base_name[:-3]
        ext = '.md'
    else:
        stem = base_name
        ext = ''

    if not find_by_name(base_name):
        return base_name

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

    new_name = name if name else artifact.name
    new_path = Path(artifact.path)
    if name and name != artifact.name:
        target_path = _artifact_path(artifact_id, new_name, artifact.mime_type)
        try:
            new_path.rename(target_path)
            new_path = target_path
        except Exception:
            new_path = Path(artifact.path)

    if content is not None:
        try:
            new_path.write_text(content)
        except Exception:
            pass

    updated = Artifact(
        id=artifact.id,
        path=str(new_path),
        name=new_name,
        mime_type=artifact.mime_type,
        content=content if content is not None else artifact.content,
        source_url=artifact.source_url,
        source_type=artifact.source_type,
        created_at=datetime.now(),
        metadata=metadata if metadata is not None else artifact.metadata,
    )

    _artifacts[artifact_id] = updated
    records = _load_index()
    updated_record = {
        "id": updated.id,
        "path": updated.path,
        "name": updated.name,
        "mime_type": updated.mime_type,
        "source_url": updated.source_url,
        "source_type": updated.source_type,
        "created_at": updated.created_at.isoformat(),
        "metadata": updated.metadata,
    }
    for idx, record in enumerate(records):
        if record.get("id") == artifact_id:
            records[idx] = updated_record
            break
    else:
        records.append(updated_record)
    _save_index(records)
    return updated


def list_artifacts() -> list[Artifact]:
    """List all artifacts, sorted by creation time (newest first)."""
    return sorted(
        _artifacts.values(),
        key=lambda a: a.created_at,
        reverse=True,
    )


def delete_artifact(artifact_id: str) -> bool:
    """Delete an artifact by ID."""
    if artifact_id in _artifacts:
        try:
            Path(_artifacts[artifact_id].path).unlink()
        except Exception:
            pass
        del _artifacts[artifact_id]
        records = _load_index()
        records = [r for r in records if r.get("id") != artifact_id]
        _save_index(records)
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
