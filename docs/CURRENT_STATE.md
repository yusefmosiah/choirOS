# ChoirOS Current State

> Snapshot as of Jan 2026 - Understanding where we are and where we're going.

---

## Quick Summary

**ChoirOS** is a web desktop environment where AI agents operate alongside users. The vision: an automatic computer that merges human intent with AI execution, versioned and observable.

**Current reality**: We have a working desktop shell with agent integration, but many features are stubs or demos. The architecture is designed but infrastructure is incomplete.

---

## Component Status

### ✅ Complete / Functional

| Component | Location | Notes |
|-----------|----------|-------|
| Desktop Shell | `choiros/src/components/desktop/` | Window manager, taskbar, icons |
| Writer App | `choiros/src/components/apps/Writer.tsx` | BlockNote editor, opens artifacts |
| Files App | `choiros/src/components/apps/Files.tsx` | Lists artifacts from API |
| Agent Harness | `supervisor/agent/harness.py` | Claude via Bedrock, tool execution |
| Agent Tools | `supervisor/agent/tools.py` | read_file, write_file, edit_file, bash |
| Event Store | `supervisor/db.py` | SQLite + NATS publishing (new) |
| FastAPI Backend | `api/main.py` | ParseURL, file serving |

### 🔄 In Progress / Partial

| Component | Location | Status |
|-----------|----------|--------|
| NATS Client (Python) | `supervisor/nats_client.py` | **NEW** - written but untested |
| NATS Client (Browser) | `choiros/src/lib/nats.ts` | **NEW** - written but untested |
| EventStream UI | `choiros/src/components/desktop/EventStream.tsx` | UI done, needs NATS hookup |
| Git Auto-Checkpoint | `supervisor/git_ops.py` | Exists but not integrated |

### 🚧 Stubs / Demos

| Component | Location | What's Needed |
|-----------|----------|--------------|
| Mail App | `choiros/src/components/apps/Mail.tsx` | Full UI with sample data, needs IMAP/SMTP backend |
| MeadowPopup | `choiros/src/components/desktop/MeadowPopup.tsx` | Demo video popup, was for external presentation |
| Terminal App | Not implemented | Would use xterm.js + PTY over WebSocket |

### 📐 Designed but Not Started

| Feature | Doc Location | Description |
|---------|--------------|-------------|
| Firecracker MicroVMs | `docs/bootstrap/FIRECRACKER.md` | Agent sandboxing on AWS bare-metal |
| TEE Deployment | `docs/bootstrap/` | SGX/SEV attestation for verifiable compute |
| Citation Economics | Scattered | USDC micropayments for prior citations |
| Multi-user Auth | Not written | GitHub OAuth + per-user SQLite |

---

## Untracked Files (from git status)

Things that exist but aren't committed:

```
choiros/
  src/components/apps/Mail.css, Mail.tsx    # UI stub
  src/components/desktop/EventStream.*      # Event notifications
  src/components/desktop/MeadowPopup.*      # Demo component
  src/lib/nats.ts                           # NEW: Browser NATS client
  src/stores/events.ts                      # Event stream store

supervisor/
  db.py                                     # MODIFIED: NATS integration
  nats_client.py                            # NEW: Python NATS wrapper
  git_ops.py                                # Git operations

docs/
  ARCHITECTURE.md                           # Core arch (updated)
  ROADMAP.md                                # Implementation phases
  THE_AGENTIC_COMPUTER.md                   # Vision doc
```

---

## Deployment Path

### Immediate (to get "hacking in public")

1. **Fix Docker build** ✅ (switched to yarn)
2. **Commit current state** - snapshot everything, clean or not
3. **Deploy to cloud** - EC2/Fly.io with docker-compose
4. **Add basic auth** - even just a shared secret to start

### Short-term (demo-ready)

5. **Test NATS integration** - verify events flow
6. **Integrate EventStream** - connect to NATS subscriptions
7. **Clean up stubs** - either implement or remove Mail, MeadowPopup
8. **Add demo content** - preloaded artifacts, agent prompts

### Medium-term (real product)

9. **Multi-user isolation** - per-user SQLite + namespaced NATS subjects
10. **Cloud filesystem sync** - S3/R2 blob storage
11. **Email integration** - real IMAP ingestion into artifacts
12. **Microvm sandboxing** - Firecracker for agent execution

---

## Key Questions to Decide

1. **What to demo first?**
   - Agent editing live UI via HMR?
   - Event stream showing agent actions?
   - Something else?

2. **What to cut?**
   - MeadowPopup (demo artifact from past presentation)?
   - Mail app (defer until backend ready)?

3. **Hosting choice?**
   - Self-managed EC2 (more control, Firecracker path)
   - Fly.io (faster to deploy, less control)
   - Railway/Render (even simpler)

4. **Auth approach for v0?**
   - Shared password (simplest)
   - GitHub OAuth (proper but more work)
   - Magic link (good UX, needs email)

---

## Next Concrete Steps

```bash
# 1. Commit everything
git add -A
git commit -m "WIP: NATS integration, Mail stub, EventStream, cleanup"

# 2. Test Docker build locally
docker-compose build

# 3. Run local test
docker-compose up
# Verify: http://localhost:5173 (desktop)
# Verify: http://localhost:8222 (NATS monitoring)
# Verify: http://localhost:8001/health (supervisor)

# 4. Deploy (example with Fly.io)
flyctl launch
flyctl deploy
```
