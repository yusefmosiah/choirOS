# ChoirOS Implementation Roadmap

## Current State (Dec 2024)

### What Works ✅
- Vite + React desktop shell with HMR
- FastAPI backend for parsing
- Supervisor managing processes
- Agent harness (Claude via Bedrock)
- File tools (read, write, edit, bash)
- WebSocket streaming responses
- Git repo on GitHub

### What's Designed but Not Built 📐
- NATS JetStream (fully spec'd in `docs/bootstrap/NATS.md`)
- SQLite per-user state (spec'd in `docs/bootstrap/STORAGE.md`)
- Firecracker isolation (spec'd in `docs/bootstrap/FIRECRACKER.md`)
- Citation economics
- TEE deployment

---

## Phase 1: Local Persistence (NOW)

**Goal**: Event-sourced state that survives restarts.

### 1.1 Add SQLite to Supervisor

```python
# supervisor/db.py
import sqlite3
from pathlib import Path

DB_PATH = Path("/Users/wiz/choirOS/state.sqlite")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            type TEXT NOT NULL,
            payload JSON NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            content_hash TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            seq INTEGER REFERENCES events(seq),
            role TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn
```

### 1.2 Log Every Event

- Agent tool calls → event
- User messages → event
- File mutations → event
- Window state → event

### 1.3 Git Auto-Commit

```bash
# After N events or T minutes
cd /Users/wiz/choirOS
git add -A
git commit -m "checkpoint: $(date +%Y%m%d-%H%M%S)"
```

---

## Phase 2: Containerization

**Goal**: Reproducible dev environment, prep for isolation.

### 2.1 Docker Compose with NATS

```yaml
# docker-compose.yml
version: '3.8'
services:
  nats:
    image: nats:2.10-alpine
    command: --jetstream --store_dir /data
    ports:
      - "4222:4222"
      - "8222:8222"  # monitoring
    volumes:
      - nats-data:/data

  choiros:
    build: .
    ports:
      - "5173:5173"
      - "8000:8000"
      - "8001:8001"
    environment:
      - NATS_URL=nats://nats:4222
    volumes:
      - ./state:/app/state
      - ./choiros/src:/app/choiros/src  # HMR still works
    depends_on:
      - nats

volumes:
  nats-data:
```

### 2.2 Event Publisher

Replace direct SQLite writes with NATS publish → materializer pattern.

### 2.3 Browser WebSocket to NATS

Use `nats.ws` in browser for real-time sync.

---

## Phase 3: Multi-User + Cloud

**Goal**: Per-user isolation, S3 sync.

### 3.1 User Auth (Simple)

- GitHub OAuth or magic link
- User ID → their SQLite file + S3 prefix

### 3.2 S3 Sync

SQLite → S3 on checkpoint.
S3 → SQLite on load.

### 3.3 Qdrant Vectors

Embed artifacts for semantic search.

---

## Phase 4: MicroVM Isolation

**Goal**: Agent code runs in Firecracker VM.

### 4.1 Agent Scheduler

NATS consumer → spawn Firecracker → return result.

### 4.2 Network Isolation

Agents can only reach NATS, nothing else.

### 4.3 Pre-baked Images

Minimal Alpine + Python + agent runtime.

---

## Phase 5: TEE + Economics

**Goal**: Verifiable computation, citation rewards.

### 5.1 TEE Attestation

SGX/SEV enclave proves untampered execution.

### 5.2 Citation Graph

Track when agents cite prior work.

### 5.3 USDC Micropayments

On-chain settlements via attestation proofs.

---

## Immediate Next Actions

1. **Init SQLite in supervisor** - 30 min
2. **Log agent events** - 30 min  
3. **Add git checkpoint command** - 30 min
4. **docker-compose with NATS** - 1 hr
5. **Event publisher** - 2 hr
6. **Browser NATS client** - 2 hr

Start with #1-3 today to get persistence working locally.
