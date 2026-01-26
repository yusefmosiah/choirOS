# ChoirOS Port Allocation

## Overview

Each worktree container gets 3 ports allocated:
- Frontend (Vite dev server)
- Backend (FastAPI)
- Supervisor (FastAPI)

## Allocation Scheme

**Known worktrees** (sequential, no overlaps):
```
main           → 5173-5175
spokane        → 5176-5178
auckland       → 5179-5181
albuquerque   → 5182-5184
curitiba      → 5185-5187
monterrey     → 5188-5190
osaka         → 5191-5193
taipei        → 5194-5196
```

**New worktrees** (checksum-based, 5200+ range):
- Uses `cksum` of worktree name
- Allocates in 5200-6200 range
- Guaranteed unique per name

## Examples

```bash
# Start spokane worktree
~/.local/bin/choiros-containerize spokane start
# → Ports: 5176 (fe), 5177 (be), 5178 (sup)

# Start new worktree
~/.local/bin/choiros-containerize feature/auth start
# → Ports: ~523X (fe), ~523X+1 (be), ~523X+2 (sup)

# Check what's running
~/.local/bin/choiros-env
```

## Accessing Services

Once container is running:
- Frontend: `http://localhost:<PORT_BASE>`
- Backend API: `http://localhost:<PORT_BASE+1>`
- API Docs: `http://localhost:<PORT_BASE+1>/docs`
- Supervisor: `http://localhost:<PORT_BASE+2>`

## Port Conflicts

If you see port conflicts:
```bash
# Check what's using ports
lsof -i :5173-6200

# Stop conflicting container
~/.local/bin/choiros-containerize <name> stop

# Or find the conflict
docker ps --format "table {{.Names}}\t{{.Ports}}"
```
