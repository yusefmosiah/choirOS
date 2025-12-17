"""Web page parser service using Trafilatura."""

import re
from urllib.parse import urlparse

import trafilatura


def sanitize_filename(title: str) -> str:
    """Sanitize title for use as filename."""
    sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
    return sanitized[:100].strip() or "untitled"


def parse_web_page(url: str) -> dict:
    """
    Parse a web page URL and extract content as markdown.

    Returns:
        dict with keys: title, content, filename, metadata

    Raises:
        ValueError: If URL cannot be fetched or parsed
    """
    # Download the page
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ValueError(f"Could not fetch URL: {url}")

    # Extract content
    result = trafilatura.extract(
        downloaded,
        output_format='markdown',
        include_links=True,
        include_images=False,
        include_tables=True,
    )

    if not result:
        raise ValueError(f"Could not extract content from: {url}")

    # Get metadata for title
    metadata = trafilatura.extract_metadata(downloaded)
    title = metadata.title if metadata and metadata.title else urlparse(url).netloc

    # Format as markdown with source header
    content = f"""# {title}

**Source:** {url}

---

{result}
"""

    filename = f"{sanitize_filename(title)}.md"

    return {
        "title": title,
        "content": content,
        "filename": filename,
        "metadata": {
            "url": url,
            "author": metadata.author if metadata else None,
            "date": metadata.date if metadata else None,
        }
    }
