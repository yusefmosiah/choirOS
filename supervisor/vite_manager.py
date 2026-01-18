"""
Vite Manager - Manages the Vite dev server subprocess.
"""

import asyncio
import os
from pathlib import Path

from .sandbox_config import build_sandbox_config
from .sandbox_provider import get_sandbox_runner
from .sandbox_runner import SandboxCommand, SandboxHandle, SandboxProcess, SandboxRunner


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
        self._sandbox_enabled = os.environ.get("CHOIR_FRONTEND_SANDBOX", "0") == "1"
        self._sandbox_runner: SandboxRunner | None = None
        self._sandbox_handle: SandboxHandle | None = None
        self._sandbox_process: SandboxProcess | None = None

    async def start(self) -> bool:
        """
        Start the Vite dev server.

        Returns True if started successfully.
        """
        async with self._lock:
            if self._process is not None and self._process.returncode is None:
                return True  # Already running

            if self._sandbox_enabled:
                try:
                    if self._sandbox_runner is None:
                        self._sandbox_runner = get_sandbox_runner()
                    if self._sandbox_handle is None:
                        config = build_sandbox_config(
                            user_id=os.environ.get("CHOIROS_USER_ID", "local"),
                            workspace_id="frontend",
                            workspace_root=str(self.vite_dir),
                            env={"FORCE_COLOR": "1"},
                        )
                        self._sandbox_handle = self._sandbox_runner.create(config)
                    command = SandboxCommand(
                        command=["npm", "run", "dev", "--", "--host", "0.0.0.0"],
                        cwd=self.vite_dir,
                        env={"FORCE_COLOR": "1"},
                        sandbox=self._sandbox_handle,
                    )
                    self._sandbox_process = self._sandbox_runner.start_process(command)
                    return True
                except Exception as e:
                    print(f"Failed to start Vite in sandbox: {e}")
                    self._sandbox_process = None
                    return False

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
            if self._sandbox_enabled and self._sandbox_runner and self._sandbox_handle and self._sandbox_process:
                try:
                    self._sandbox_runner.stop_process(
                        self._sandbox_handle,
                        self._sandbox_process.process_id,
                    )
                except Exception as e:
                    print(f"Failed to stop sandboxed Vite: {e}")
                finally:
                    self._sandbox_process = None
                if os.environ.get("CHOIR_FRONTEND_SANDBOX_KEEP", "0") != "1":
                    try:
                        self._sandbox_runner.destroy(self._sandbox_handle)
                    except Exception as e:
                        print(f"Failed to destroy frontend sandbox: {e}")
                    self._sandbox_handle = None
                return
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
        if self._sandbox_enabled:
            return self._sandbox_process is not None
        return self._process is not None and self._process.returncode is None
