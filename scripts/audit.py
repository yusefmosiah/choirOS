
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supervisor.agent.auditor import UnilateralAuditor

async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/audit.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)

    print(f"🔍 Auditor running on: {file_path}")
    print("..." * 10)

    auditor = UnilateralAuditor()
    try:
        result = await auditor.audit_file(file_path)

        print("\n📝 AUDIT RESULT:")
        print(f"Mode: {result.mode}")
        print("\nCRITIQUE:")
        print(result.critique)

        if result.blind_spots:
            print("\nBLIND SPOTS:")
            for spot in result.blind_spots:
                print(f"- {spot}")

        if result.citations:
            print("\nCITATIONS:")
            for cite in result.citations:
                print(f"- {cite}")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())
