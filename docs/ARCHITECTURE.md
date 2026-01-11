# ChoirOS Architecture

ChoirOS implements the **Automatic Computer** as a personal mainframe: a sandboxed runtime where the shell, agent, and version control live together so the system can modify itself and recover deterministically.

## Evolution Path

```
Local Dev → Container → MicroVM → TEE
    ↓          ↓          ↓        ↓
  File I/O   Docker    Firecracker  SGX/SEV
             Volumes    rootfs      Encrypted
```

## Core Data Flow

```
┌─────────────┐     ┌─────────────────────────────────┐
│   Browser   │────▶│         Supervisor              │
│  (Vite HMR) │◀────│  WebSocket + File Ops + Agent   │
└─────────────┘     └───────────────┬─────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │        Event Log (NATS)       │
                    │   JetStream append-only log   │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │  User A   │   │  User B   │   │  User C   │
            │  SQLite   │   │  SQLite   │   │  SQLite   │
            │ (view)    │   │ (view)    │   │ (view)    │
            └─────┬─────┘   └───────────┘   └───────────┘
                  │
                  ▼
            ┌───────────┐       ┌───────────┐
            │ Filesystem│──────▶│    Git    │
            │  (mount)  │       │  (commit) │
            └───────────┘       └───────────┘
                                     │
                                     ▼
                              ┌───────────┐
                              │  Blobs    │
                              │ S3/R2 URL │
                              └───────────┘
```

## NATS as Source of Truth

NATS is the authoritative event log. SQLite, filesystem, and UI are projections that can be rebuilt from the event stream. Time travel is event replay, not git history.

**Principles**
- Event-first: every mutation emits a NATS event with user + source
- Deterministic replay: projections rebuild from events or snapshots
- Undo is an event: `UNDO` targets a sequence, projections rewind

**Write Path (Hybrid Evolution)**
- Short-term: direct writes remain, but events are emitted synchronously
- Mid-term: artifacts and source files are written by the projector
- Long-term: projector-only writes for durable state

**Event Streams**
- Subjects are per user: `choiros.{user_id}.{source}.{type}`
- Durable consumers per projection for resumable rebuilds
- Snapshots (SQLite + filesystem) speed up replay

## Event Types

```typescript
type ChoirEvent = 
  | { type: 'file.write', path: string, content_hash: string, blob_url?: string }
  | { type: 'file.delete', path: string }
  | { type: 'conversation.message', role: 'user' | 'assistant', content: string }
  | { type: 'tool.call', name: string, params: object, result: string }
  | { type: 'window.open', id: string, component: string, position: object }
  | { type: 'window.close', id: string }
  | { type: 'checkpoint', commit_sha: string }
```

## Per-User SQLite Schema

```sql
-- Materialized from JetStream events
CREATE TABLE events (
    seq INTEGER PRIMARY KEY,        -- NATS sequence number
    timestamp TEXT NOT NULL,
    type TEXT NOT NULL,
    payload JSON NOT NULL
);

-- Derived tables (rebuilt from events)
CREATE TABLE files (
    path TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    blob_url TEXT,                  -- NULL if inline
    updated_at TEXT NOT NULL
);

CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    title TEXT
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id),
    seq INTEGER REFERENCES events(seq),
    role TEXT NOT NULL,
    content TEXT NOT NULL
);

-- Virtual filesystem (view)
CREATE VIEW fs AS
SELECT 
    path,
    CASE 
        WHEN blob_url IS NOT NULL THEN blob_url
        ELSE (SELECT content FROM inline_content WHERE hash = content_hash)
    END as content
FROM files;
```

## Git Integration

Each user gets a git repo that represents their materialized state. Checkpoints are exposed through the supervisor API and GitPanel UI for in-app version control.

```bash
# Structure
/users/{user_id}/
├── .git/
├── .choir/
│   ├── state.sqlite     # Per-user materialized view
│   └── config.toml      # User preferences
├── artifacts/           # Parsed content
├── conversations/       # Exported chat logs
└── workspace/           # Their actual files
```

### Commit Strategy

1. **Auto-commit**: After N events or T time
2. **Manual commit**: User requests checkpoint
3. **Before deploy**: Always commit + push

```python
async def checkpoint(user_id: str, message: str = "checkpoint"):
    """Create git commit from current state."""
    repo_path = f"/users/{user_id}"
    
    # Materialize any pending events to filesystem
    await materialize_pending(user_id)
    
    # Git operations
    subprocess.run(["git", "add", "-A"], cwd=repo_path)
    subprocess.run(["git", "commit", "-m", message], cwd=repo_path)
    
    # Push to remote (user's fork or managed repo)
    subprocess.run(["git", "push"], cwd=repo_path)
    
    # Record checkpoint event
    await publish_event(user_id, {
        "type": "checkpoint",
        "commit_sha": get_head_sha(repo_path)
    })
```

## Blob Storage

Large content → hash → upload → store URL

```python
async def store_blob(content: bytes) -> str:
    """Store content in S3/R2, return URL."""
    content_hash = hashlib.sha256(content).hexdigest()
    key = f"blobs/{content_hash[:2]}/{content_hash}"
    
    # Check if exists (content-addressed = idempotent)
    if not await blob_exists(key):
        await upload_blob(key, content)
    
    return f"s3://choir-blobs/{key}"
```

Threshold: ~64KB inline, larger → blob URL

## Container → MicroVM → TEE

### Phase 1: Container (Current)
- Docker with volume mounts
- SQLite on host filesystem
- Git via subprocess

### Phase 2: MicroVM (Firecracker)
- Minimal kernel + rootfs
- Virtio-fs for shared storage
- NATS over VSOCK

### Phase 3: TEE (SGX/SEV)
- Encrypted memory
- Attestation before key release
- Sealed storage for SQLite

```yaml
# firecracker config
kernel: /images/vmlinux
rootfs: /images/choiros-rootfs.ext4
vsock:
  guest_cid: 3
  uds_path: /tmp/firecracker.sock
```

## Configuration Management

```toml
# /etc/choir/config.toml

[runtime]
mode = "container"  # local | container | microvm | tee

[storage]
events_url = "nats://localhost:4222"
stream = "CHOIR"
blobs_url = "s3://choir-blobs"

[git]
remote_template = "https://github.com/{user}/choir-state.git"
auto_commit_interval = 300  # seconds
auto_commit_threshold = 50  # events

[tee]
attestation_server = "https://attest.choir.dev"
key_server = "https://keys.choir.dev"
```

## Next Steps

1. [x] Git repo initialized
2. [x] Supervisor git endpoints + UI checkpointing
3. [ ] Add NATS to docker-compose + browser client wiring
4. [ ] Event materializer + blob storage integration
5. [ ] In-app deploy pipeline (git push → CI/CD → redeploy)
6. [ ] Firecracker spike
7. [ ] TEE attestation PoC
