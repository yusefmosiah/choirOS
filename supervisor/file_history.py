"""
File History - Tracks file changes for undo functionality.

Simple in-memory implementation with deque for each file.
"""

import asyncio
import shutil
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class FileSnapshot:
    """A snapshot of a file's state."""
    path: str
    content: Optional[bytes]  # None if file didn't exist
    timestamp: datetime


class FileHistory:
    """Manages file history for undo operations."""

    MAX_HISTORY_PER_FILE = 50

    def __init__(self):
        self._history: dict[str, deque[FileSnapshot]] = {}
        self._lock = asyncio.Lock()

    async def save_state(self, path: str) -> None:
        """
        Save the current state of a file before modification.

        Call this BEFORE making any changes to a file.
        """
        async with self._lock:
            file_path = Path(path)

            # Read current content (or None if doesn't exist)
            content = None
            if file_path.exists():
                content = file_path.read_bytes()

            snapshot = FileSnapshot(
                path=path,
                content=content,
                timestamp=datetime.now(),
            )

            # Initialize deque for this file if needed
            if path not in self._history:
                self._history[path] = deque(maxlen=self.MAX_HISTORY_PER_FILE)

            self._history[path].append(snapshot)

    async def undo(self, count: int = 1) -> list[str]:
        """
        Undo the last N changes across all files.

        Returns list of restored file paths.
        """
        async with self._lock:
            restored = []

            # Get all snapshots sorted by timestamp (newest first)
            all_snapshots = []
            for path, snapshots in self._history.items():
                for snapshot in snapshots:
                    all_snapshots.append((snapshot, path))

            all_snapshots.sort(key=lambda x: x[0].timestamp, reverse=True)

            # Restore the most recent N snapshots
            for i, (snapshot, path) in enumerate(all_snapshots[:count]):
                file_path = Path(snapshot.path)

                if snapshot.content is None:
                    # File didn't exist before - delete it
                    if file_path.exists():
                        file_path.unlink()
                else:
                    # Restore previous content
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_bytes(snapshot.content)

                restored.append(snapshot.path)

                # Remove this snapshot from history
                if path in self._history and self._history[path]:
                    self._history[path].pop()

            return restored

    def size(self) -> int:
        """Return total number of snapshots across all files."""
        return sum(len(q) for q in self._history.values())

    def clear(self) -> None:
        """Clear all history."""
        self._history.clear()
