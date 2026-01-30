
import asyncio
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from supervisor.event_publisher import get_publisher

async def main():
    try:
        publisher = get_publisher()
        path = "docs/DEPLOYMENT_PLAN.md"
        content = b"Simulated content update for testing polling worker"

        print(f"📡 Appending file.write event for {path}...")
        seq = await publisher.log_file_write_async(path, content)
        print(f"✅ Event published to NATS (Seq: {seq})")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
