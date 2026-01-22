
import asyncio
import sys
import uuid
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from supervisor.db import get_store

async def main():
    try:
        store = get_store()
        print("✅ Connected to EventStore")

        path = "docs/DEPLOYMENT_PLAN.md"
        content = b"Simulated content update for testing polling worker"

        print(f"📡 Appending file.write event for {path}...")

        # We use the synchronous append for simplicity in this script,
        # or the async wrapper if available.
        # But get_store() returns EventStore instance which has log_file_write.

        # log_file_write is sync in the class definition shown in db.py (unless using async wrapper)
        # Wait, log_file_write is defined as synchronous "def log_file_write".

        seq = store.log_file_write(path, content)
        print(f"✅ Event committed to SQLite (Seq: {seq})")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
