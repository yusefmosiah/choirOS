"""
Vite Manager - Manages the Vite dev server subprocess.
"""

import asyncio
import os
from pathlib import Path


def _get_project_root() -> Path:
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        return Path(pythonpath.split(":")[0])
    return Path(__file__).parent.parent


class ViteManager:
    """Manages the Vite development server subprocess."""

    def __init__(self):
        self.vite_dir = _get_project_root() / "choiros"
        self._process: asyncio.subprocess.Process | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> bool:
        """
        Start the Vite dev server.

        Returns True if started successfully.
        """
        async with self._lock:
            if self._process is not None and self._process.returncode is None:
                return True  # Already running

            try:
                self._process = await asyncio.create_subprocess_exec(
                    "npm", "run", "dev", "--", "--host", "0.0.0.0",
                    cwd=str(self.vite_dir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    env={**os.environ, "FORCE_COLOR": "1"},
                )

                # Wait a moment and check if it started
                await asyncio.sleep(2)

                if self._process.returncode is None:
                    return True
                else:
                    return False

            except Exception as e:
                print(f"Failed to start Vite: {e}")
                return False

    async def stop(self) -> None:
        """Stop the Vite dev server."""
        async with self._lock:
            if self._process is not None:
                self._process.terminate()
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self._process.kill()
                    await self._process.wait()
                self._process = None

    async def restart(self) -> bool:
        """Restart the Vite dev server."""
        await self.stop()
        return await self.start()

    def is_running(self) -> bool:
        """Check if the Vite dev server is running."""
        return self._process is not None and self._process.returncode is None
