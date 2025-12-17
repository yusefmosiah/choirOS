# ChoirOS Phase 3: Agent Platform Architecture

> Unified sandbox. Supervisor pattern. Simple tools.

---

## Core Decisions

### 1. Unified Sandbox

Agent + ChoirOS shell run in a single sandbox.

**Why not separate?**
- Prompt injection is the model labs' problem
- A compromised agent already owns the sandbox—separation doesn't help
- Simpler architecture, no file sync complexity

### 2. Supervisor Process Pattern

Two processes in the sandbox:

| Process | Role | Can Crash? |
|---------|------|------------|
| **Supervisor** | Manages file history, handles undo, restarts Vite | No |
| **Vite + Agent** | Serves UI, runs agent, edits files | Yes |

### 3. Auth Isolation

Auth tokens live in a separate layer the agent cannot access. Agent receives sanitized user input only.

### 4. Undo Works Even If UI Crashes

Browser → Supervisor (port 8001) → restores files → restarts Vite → browser reconnects.

### 5. Files Are Files

Agent edits files directly on disk. Events are for timeline/coordination, not storage.

### 6. Data Sovereignty

Self-hosted only. Docker for dev, Firecracker on EC2 for prod. No E2B, Modal, or third-party sandbox services.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                        Sandbox                                │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Auth Proxy (isolated)                                  │  │
│  │    └── Session tokens, never exposed to agent           │  │
│  └────────────────────────────────────────────────────────┘  │
│                            │                                  │
│                            │ (user_id only)                   │
│                            ▼                                  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Supervisor (port 8001)                                 │  │
│  │    └── File history (SQLite or in-memory)               │  │
│  │    └── Undo endpoint                                    │  │
│  │    └── Vite process manager                             │  │
│  └────────────────────────────────────────────────────────┘  │
│                            │                                  │
│                            │ (manages)                        │
│                            ▼                                  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Vite + Agent (port 5173)                               │  │
│  │    └── Serves React shell to browser                    │  │
│  │    └── Agent writes files to disk                       │  │
│  │    └── HMR updates browser on file change               │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                            │
                            │ WebSocket (HMR) + HTTP (undo)
                            ▼
                    ┌──────────────┐
                    │   Browser    │
                    └──────────────┘
```

---

## Security Model

| Concern | Position |
|---------|----------|
| Prompt injection | Model labs' problem |
| Session compromise | Same as any web app. Auth isolated from agent. |
| Agent writes bad code | Undo solves it. Not a security issue. |
| Wallet deception | Lit/Vincent policies + trusted UI |

---

## Implementation Phases

| Phase | Goal | What to Build |
|-------|------|---------------|
| **3.1** | Agent writes files | Docker + Supervisor + Agent harness |
| **3.2** | Vibecoding works | Theme modification → HMR → live update |
| **3.3** | Undo works | File history + undo endpoint + UI |
| **3.4** | Production | Firecracker on EC2, S3 backup |

---

*Created: 2025-12-17*
