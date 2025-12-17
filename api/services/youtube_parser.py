"""YouTube transcript parser service."""

import re
from urllib.parse import urlparse, parse_qs
from typing import Optional

from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp


def extract_video_id(url: str) -> Optional[str]:
    """Extract and validate video ID from YouTube URL."""
    # Remove any backslashes that might be from shell escaping
    clean_url = url.replace('\\', '')
    url_data = urlparse(clean_url)

    # Check for youtu.be shortened URLs
    if url_data.hostname == 'youtu.be':
        video_id = url_data.path[1:].split('?')[0]
        return video_id if len(video_id) == 11 else None

    # Handle youtube.com URLs
    if url_data.hostname and 'youtube.com' in url_data.hostname:
        path_segments = url_data.path.split('/')

        # Check for common URL patterns
        patterns = [
            ('/live/', 2),
            ('/embed/', 2),
            ('/v/', 2),
            ('/watch/', 2),
            ('/shorts/', 2),
            ('/watch', 'v')
        ]

        for pattern, index in patterns:
            if url_data.path.startswith(pattern):
                if isinstance(index, int):
                    return path_segments[index].split('?')[0]
                else:
                    query = parse_qs(url_data.query)
                    return query.get(index, [None])[0]

    # Fallback: search for 11-character video ID pattern
    match = re.search(r'[0-9A-Za-z_-]{11}', url_data.path + url_data.query)
    return match.group(0) if match else None


def get_video_title(video_id: str) -> str:
    """Get video title using yt-dlp."""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            return info.get('title', video_id) if info else video_id
    except Exception:
        return video_id


def sanitize_filename(title: str) -> str:
    """Sanitize title for use as filename."""
    # Remove or replace problematic characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
    # Truncate to reasonable length
    return sanitized[:100].strip()


def parse_youtube(url: str) -> dict:
    """
    Parse a YouTube URL and extract transcript.

    Returns:
        dict with keys: title, content, filename, metadata

    Raises:
        ValueError: If URL is invalid or transcript unavailable
    """
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError(f"Invalid YouTube URL: {url}")

    # Get video title
    title = get_video_title(video_id)

    # Get transcript using new API (v1.0+)
    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id)
        # New API returns FetchedTranscriptSnippet objects
        text = ' '.join([snippet.text for snippet in transcript])
    except Exception as e:
        raise ValueError(f"Could not get transcript: {str(e)}")

    # Format as markdown
    content = f"""# {title}

**Source:** {url}

---

{text}
"""

    filename = f"{sanitize_filename(title)}.md"

    return {
        "title": title,
        "content": content,
        "filename": filename,
        "metadata": {
            "video_id": video_id,
            "transcript_length": len(transcript),
        }
    }


def is_youtube_url(url: str) -> bool:
    """Check if URL is a YouTube URL."""
    parsed = urlparse(url)
    if not parsed.hostname:
        return False
    return 'youtube.com' in parsed.hostname or parsed.hostname == 'youtu.be'
