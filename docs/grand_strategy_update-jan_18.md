# Grand Strategy Update — Jan 18, 2026

## Where We Are

ChoirOS is now past its bootstrap infrastructure phase. The core scaffolding for **version-controlled workspaces** and **isolated sandboxes** is in place and tested. What was speculative architecture two weeks ago is now concrete code with test coverage.

The system can now:
- Create checkpoints of supervisor workspace state and diff between them
- Create sandboxed execution environments via sprites.dev (or locally)
- Run commands inside sandboxes, checkpoint them, restore to previous states
- Wire sandbox lifecycle into the run orchestrator for rollback on failure

This is the foundational layer everything else builds on.

## The Architecture in Motion

```
┌─────────────────────────────────────────────────────────────────┐
│                        ChoirOS Host                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐   │
│  │  Frontend (React)│  │  API (FastAPI)   │  │ Supervisor  │   │
│  │                  │  │                  │  │             │   │
│  └────────┬─────────┘  └────────┬─────────┘  └──────┬──────┘   │
│           │                     │                    │          │
│           └─────────────────────┼────────────────────┘          │
│                                 │                               │
│                    ┌────────────▼────────────┐                  │
│                    │   Event Store / NATS    │                  │
│                    └────────────┬────────────┘                  │
└─────────────────────────────────┼────────────────────────────────┘
                                  │
                    ┌────────────▼────────────┐
                    │  Version Control Layer  │ ◄── Checkpoints, Diff, Rollback
                    │     (git_ops.py)        │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    Sandbox Provider     │ ◄── Local or sprites.dev
                    │  (sandbox_provider.py)  │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Inner Sandbox VM      │ ◄── React frontend goes here
                    │   (sprites.dev)         │
                    └─────────────────────────┘
```

The architecture now supports the key invariant: **bad code cannot corrupt the host**. All execution happens inside isolated sandboxes that can be rolled back on failure.

## What Just Landed

- **VC primitives**: checkpoint(), diff_between(), git_revert() — 150 lines of git operations with choirignore support and event store integration
- **Sandbox abstraction**: LocalSandboxRunner + SpritesSandboxRunner with uniform create/exec/checkpoint/restore interface
- **Sprites adapter**: Full HTTP API wrapper for sprites.dev — create sprites, exec commands, checkpoint, restore, proxy tunnels
- **Orchestrator integration**: RunOrchestrator now creates sandboxes, checkpoints before runs, restores on failure, destroys after
- **Frontend scaffolding**: Terminal app component that will eventually run inside the inner sandbox
- **Test coverage**: 400+ lines across test_sprites_adapter.py, test_sandbox_runner.py, test_sandbox_provider.py, test_run_orchestrator.py

## Trajectory: What's Next

**Immediate (This Sprint)**
1. Wire checkpoint/restore into the run flow end-to-end
2. Get React frontend running inside the inner sandbox
3. Implement screenshot slideshow testing for verification artifacts

**Near Term (Next 2-3 Sprints)**
- Passkey auth + recovery (email/WhatsApp/Telegram channels)
- Security-by-design audit for chat I/O and MCP boundaries
- NATS credential rotation (short-lived, per-session)

**Beyond (Phase 2-3)**
- Terminal that controls inner VM directly
- OS connector (mount Choir as drive)
- Media controls, filesystem mindmaps, AWS integration

## The Invariant We're Building Toward

ChoirOS is an **agentic operating system** where:
- Every state change is checkpointed
- Bad executions are automatically rolled back
- The host is never compromised by sandbox escapes
- Users can recover from any failure in one click

We're now 40% toward that invariant. The checkpoint/restore mechanisms exist. The sandbox isolation exists. The wiring exists. What remains is tightening the integration and extending the isolation guarantees to the frontend layer.

## Health Check

| Component | Status |
|-----------|--------|
| Version Control | ✅ Implemented and tested |
| Sandbox Isolation | ✅ Implemented, provider wired |
| Orchestrator Integration | ✅ Core flow wired |
| Auth (Bootstrap) | ⚠️ Stubs in place, crypto pending |
| NATS Hardening | ⚠️ Phase 0 done, per-session creds pending |
| Frontend-in-Sandbox | 🔲 Terminal UI exists, full isolation pending |
| Verification Artifacts | 🔲 Screenshot slideshow not started |

The architecture is sound. The code is clean. The trajectory is clear.
