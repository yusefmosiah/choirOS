"""Document parser service using MarkItDown."""

import re
import tempfile
import os
from pathlib import Path

from markitdown import MarkItDown


def sanitize_filename(name: str) -> str:
    """Sanitize for use as filename."""
    sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
    return sanitized[:100].strip() or "untitled"


def parse_document(file_content: bytes, original_filename: str) -> dict:
    """
    Parse a document file and convert to markdown.

    Supports: PDF, DOCX, PPTX, XLSX, images, audio, and more.

    Returns:
        dict with keys: title, content, filename, metadata

    Raises:
        ValueError: If file cannot be parsed
    """
    # Get base name without extension
    base_name = Path(original_filename).stem
    extension = Path(original_filename).suffix.lower()

    # Write to temp file (MarkItDown needs file path)
    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    try:
        # Parse with MarkItDown
        md = MarkItDown()
        result = md.convert(tmp_path)

        if not result or not result.text_content:
            raise ValueError(f"Could not extract content from: {original_filename}")

        # Format content
        title = base_name
        content = f"""# {title}

**Original file:** {original_filename}

---

{result.text_content}
"""

        filename = f"{sanitize_filename(base_name)}.md"

        return {
            "title": title,
            "content": content,
            "filename": filename,
            "metadata": {
                "original_filename": original_filename,
                "original_extension": extension,
            }
        }

    finally:
        # Clean up temp file
        os.unlink(tmp_path)


def get_supported_extensions() -> list[str]:
    """Get list of supported file extensions."""
    return [
        ".pdf",
        ".docx", ".doc",
        ".pptx", ".ppt",
        ".xlsx", ".xls",
        ".html", ".htm",
        ".txt", ".md",
        ".json",
        ".xml",
        ".csv",
        ".jpg", ".jpeg", ".png", ".gif", ".webp",
        ".mp3", ".wav", ".m4a",
    ]
