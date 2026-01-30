import asyncio
import json
import os
import sys
from datetime import datetime

import websockets


async def main() -> None:
    url = os.environ.get("CHOIR_WS_URL", "ws://localhost:8001/agent")
    print(f"[{datetime.now().isoformat()}] Connecting to {url}", flush=True)
    async with websockets.connect(url) as ws:
        print(f"[{datetime.now().isoformat()}] Connected. Listening...", flush=True)
        while True:
            try:
                msg = await ws.recv()
            except websockets.ConnectionClosed:
                print(f"[{datetime.now().isoformat()}] Connection closed", flush=True)
                return
            # Drop messages to avoid backpressure
            if isinstance(msg, bytes):
                continue
            try:
                payload = json.loads(msg)
            except json.JSONDecodeError:
                continue
            # Lightweight progress output
            if payload.get("type") in {"error", "verification"}:
                print(json.dumps(payload, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
