
import asyncio
import json
import logging
import signal
import sys
from pathlib import Path

# Add project root to path
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from supervisor.db import get_store
from supervisor.agent.auditor import UnilateralAuditor

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("auditor-worker")

class AuditorWorker:
    def __init__(self):
        self.auditor = UnilateralAuditor()
        self.store = get_store()
        self.running = True
        self.last_seq = self.store.get_latest_seq()

    async def start(self):
        """Poll SQLite for new events."""
        logger.info(f"Starting SQLite Polling Worker. Latest Seq: {self.last_seq}")

        while self.running:
            try:
                # Fetch new events
                new_events = self.store.get_events(since_seq=self.last_seq, limit=10)

                for event in new_events:
                    seq = event["seq"]
                    self.last_seq = max(self.last_seq, seq)

                    if event["type"] == "file.write":
                        await self.handle_file_write(event)

                if not new_events:
                    await asyncio.sleep(2) # Backoff if no events
                else:
                    await asyncio.sleep(0.1) # Fast poll if active

            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(5)

    async def handle_file_write(self, event: dict):
        """Handle a file write event."""
        try:
            payload = json.loads(event["payload"])
            path = payload.get("path", "")

            # Filter boring files
            if any(x in path for x in [".git", "node_modules", ".DS_Store", "__pycache__"]):
                return

            logger.info(f"Auditing change to: {path}")

            # Run Auditor
            result = await self.auditor.audit_file(path)

            # Log findings
            logger.info(f"Audit Complete for {path}. Mode: {result.mode}")

            # Store result as a note in DB
            self.store.append("auditor.critique", {
                "path": path,
                "mode": result.mode,
                "critique": result.critique,
                "blind_spots": result.blind_spots,
                "citations": result.citations
            }, source="auditor")

        except Exception as e:
            logger.error(f"Error handling file write: {e}")

    async def stop(self):
        self.running = False

if __name__ == "__main__":
    worker = AuditorWorker()

    def signal_handler():
        asyncio.create_task(worker.stop())

    try:
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        pass
