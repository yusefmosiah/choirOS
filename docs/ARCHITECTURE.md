# ChoirOS Architecture

ChoirOS implements the **Automatic Computer** as a dual-sandbox system: a Director loop supervises an Associate loop. Both are agentic Ralph loops, but only the Associate edits the repo and runs commands. Time travel in v0 is git-based.

## Evolution Path

```
Local Dev → Container → MicroVM → TEE
    ↓          ↓          ↓        ↓
  File I/O   Docker    Firecracker  SGX/SEV
             Volumes    rootfs      Encrypted
```

## Core Data Flow

```
┌───────────────┐     ┌────────────────────────────┐
│   Browser     │────▶│     Control Plane UI       │
└───────────────┘     └───────────────┬────────────┘
                                      │
                                      ▼
                         ┌──────────────────────┐
                         │   Director Sandbox   │
                         │  (planner + policy)  │
                         └───────────┬──────────┘
                                     │ DirectorTask
                                     ▼
                         ┌──────────────────────┐
                         │   Associate Sandbox  │
                         │  (Vite + repo + tools)│
                         └───────────┬──────────┘
                                     │ AssociateResult
                                     ▼
                             ┌─────────────┐
                             │     Git     │
                             │ checkpoints │
                             └─────────────┘
```

## Time Travel (v0)

Time travel is git-based. The Director requests git actions as Associate tasks.
All state changes flow through the Associate sandbox and are checkpointed in git.

## Future: Event Log

NATS event sourcing and filesystem snapshots are deferred. When introduced, they
will complement git checkpoints rather than replace the Director/Associate loop.

## Task Contracts

Director/Associate contracts are defined in `docs/ralph/CONTRACTS.md`.

## Deferred: Event Log Schema

Event sourcing and materialized projections are deferred in v0. The schema will
be defined when NATS and snapshots are reintroduced.

## Git Integration

Each user gets a git repo inside the Associate sandbox. Git checkpoints are the
time travel mechanism and the primary state history.

```bash
# Structure
/workspaces/{user_id}/
├── .git/
├── choiros/             # ChoirOS app and UI
├── artifacts/           # Parsed content (optional)
└── workspace/           # User files
```

### Commit Strategy

1. **Auto-commit**: After N tasks or T time
2. **Manual commit**: User requests checkpoint
3. **Before deploy**: Always commit + push

```python
async def checkpoint(user_id: str, message: str = "checkpoint"):
    """Create git commit from current state."""
    repo_path = f"/users/{user_id}"
    
    # Git operations
    subprocess.run(["git", "add", "-A"], cwd=repo_path)
    subprocess.run(["git", "commit", "-m", message], cwd=repo_path)
    
    # Push to remote (user's fork or managed repo)
    subprocess.run(["git", "push"], cwd=repo_path)
    
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
- Control plane channel over VSOCK

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
blobs_url = "s3://choir-blobs"

[git]
remote_template = "https://github.com/{user}/choir-state.git"
auto_commit_interval = 300  # seconds
auto_commit_threshold = 50  # tasks

[tee]
attestation_server = "https://attest.choir.dev"
key_server = "https://keys.choir.dev"
```

## Next Steps

1. [x] Git repo initialized
2. [x] Supervisor git endpoints + UI checkpointing
3. [ ] Director <-> Associate task protocol
4. [ ] Sprites sandbox adapter
5. [ ] In-app deploy pipeline (git push → CI/CD → redeploy)
6. [ ] Firecracker spike
7. [ ] TEE attestation PoC
