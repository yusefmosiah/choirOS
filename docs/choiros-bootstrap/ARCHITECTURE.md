# ChoirOS Architecture

> A distributed web desktop that appears local but runs globally.

## The Paradigm: The Kernel Analogy

> **"The Model is the Kernel. The Chatbot is the CLI. The Agentic Computer is the GUI."**

ChoirOS implements the "User Space" layer—the window manager, process scheduler, and persistence engine that protects users from the raw LLM kernel and manages long-running agent tasks.

## Core Principles

1. **Local shell, remote brain** - Browser renders UI, all compute happens in cloud
2. **Per-user sovereign data** - Each user has their own SQLite synced to S3
3. **NATS as the kernel's syscalls** - All events flow through a global log stream
4. **Isolated agents** - Every agent runs in a Firecracker microVM
5. **Intent over Application** - Users express intents ("?"), agents vibecode solutions
6. **Collaborative Caching (Thought Bank)** - Agents publish artifacts to shared network, receive micropayments on citation

---

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser (ChoirOS Shell)                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────────┐ │
│  │ Writer  │ │  Files  │ │Terminal │ │    ? Command Bar    │ │
│  └────┬────┘ └────┬────┘ └────┬────┘ └──────────┬──────────┘ │
│       └───────────┴───────────┴─────────────────┘            │
│                              │                                │
│              ┌───────────────┼───────────────┐                │
│              │     Zustand State Stores      │                │
│              │  ┌─────────┐ ┌─────────────┐  │                │
│              │  │ sql.js  │ │  nats.ws    │  │                │
│              │  │ (cache) │ │  (events)   │  │                │
│              │  └─────────┘ └─────────────┘  │                │
│              └───────────────┬───────────────┘                │
└──────────────────────────────┼────────────────────────────────┘
                               │ WebSocket
          ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                         AWS                                   │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              NATS JetStream (EC2 cluster)              │  │
│  │         Subjects: user.*, agent.*, system.*            │  │
│  └───────────────────────┬────────────────────────────────┘  │
│              ┌───────────┼───────────┬───────────┐           │
│              ▼           ▼           ▼           ▼           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────┐ ┌───────────┐   │
│  │     S3      │ │   Qdrant    │ │ Gateway │ │  Agent    │   │
│  │  (per-user  │ │  (vectors)  │ │  (API)  │ │  Pool     │   │
│  │   sqlite +  │ │             │ │         │ │(Firecracker│   │
│  │  artifacts) │ │             │ │         │ │  microVMs)│   │
│  └─────────────┘ └─────────────┘ └─────────┘ └───────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. User Action → NATS → Agents

```
User clicks "Summarize this" in Writer
    │
    ▼
Browser emits to NATS:
    Subject: user.{user_id}.action
    Payload: {
        type: "SUMMARIZE_REQUEST",
        artifact_id: "abc123",
        content: "...",
        timestamp: 1702345678
    }
    │
    ▼
Agent Pool receives event, spawns Firecracker VM:
    - Mounts user's S3 artifacts (read-only)
    - Runs summarization task
    - Emits result to NATS
    │
    ▼
Browser receives:
    Subject: agent.{agent_run_id}.result
    Payload: {
        type: "SUMMARY_COMPLETE",
        artifact_id: "abc123",
        summary: "...",
        citations: [...]
    }
    │
    ▼
UI updates, SQLite cache updates, syncs to S3
```

### 2. State Sync (SQLite ↔ S3)

```
Local Change:
    Zustand store updates → sql.js writes →
    debounced sync → PUT to S3 (user/{id}/workspace.sqlite)

Remote Change (from agent):
    S3 event → NATS notification →
    Browser fetches delta → sql.js applies → Zustand updates
```

---

## Component Responsibilities

### Browser (Frontend)

| Component | Responsibility |
|-----------|----------------|
| **Window Manager** | z-index, focus, drag/resize, minimize/maximize |
| **Desktop Shell** | Icons, wallpaper, layout |
| **Taskbar** | Running apps, `?` command bar, system tray |
| **Apps** | Writer (TipTap), Files, Terminal (xterm.js) |
| **State Layer** | Zustand stores, sql.js cache, NATS client |

### AWS (Backend)

| Component | Responsibility |
|-----------|----------------|
| **NATS JetStream** | Event bus, log stream, pub/sub |
| **S3** | Per-user SQLite, artifacts (docs, images) |
| **Qdrant** | Vector embeddings for semantic search |
| **API Gateway** | Auth, REST endpoints, WebSocket upgrade |
| **Agent Pool** | Firecracker VMs, task execution, isolation |

---

## Security Boundaries

```
┌─────────────────────────────────┐
│         User's Browser          │  ◄── Untrusted
│    (renders, caches, emits)     │
└───────────────┬─────────────────┘
                │ TLS + JWT
                ▼
┌─────────────────────────────────┐
│         API Gateway             │  ◄── Auth boundary
│    (validates, rate limits)     │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│         NATS JetStream          │  ◄── Subject-level ACLs
│   (user.X.* only by user X)     │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│       Firecracker microVM       │  ◄── Hard isolation
│   (no network except NATS,      │
│    read-only artifact mounts,   │
│    ephemeral, killed after run) │
└─────────────────────────────────┘
```

---

## Key Design Decisions

### Why NATS JetStream (not Kafka, Redis)?

- **Lightweight**: Single binary, runs on t3.small
- **WebSocket native**: nats.ws works directly in browser
- **JetStream**: Durable streams, replay from any point
- **Subject hierarchy**: Natural for `user.*`, `agent.*`, `system.*`

### Why Firecracker (not Docker, gVisor)?

- **Hard VM isolation**: Different kernel, can't escape
- **Fast boot**: ~125ms cold start
- **AWS native**: Same tech as Lambda, well-supported on EC2
- **Minimal overhead**: ~5MB memory overhead per VM

### Why Per-User SQLite (not Postgres multi-tenant)?

- **Sovereignty**: User owns their database file
- **Portability**: Export = download one file
- **Performance**: No network round-trips for reads
- **Simplicity**: No connection pooling, no ORM

### Why Qdrant (not Pinecone, Weaviate)?

- **Self-hosted**: Runs in AWS, no data leaves
- **Rust-based**: Fast, reliable
- **Simple API**: REST + gRPC
- **Filtering**: Metadata filters on vector search

---

## Scaling Considerations

| Component | Scaling Strategy |
|-----------|------------------|
| **NATS** | Cluster mode, 3-node minimum for HA |
| **S3** | Infinite (AWS manages) |
| **Qdrant** | Horizontal sharding by user_id prefix |
| **Firecracker** | EC2 .metal auto-scaling group |
| **Frontend** | Static assets on CloudFront |

---

## Next Steps

See companion docs:
- [STACK.md](./STACK.md) - Detailed technology choices
- [NATS.md](./NATS.md) - Event schemas and subjects
- [FIRECRACKER.md](./FIRECRACKER.md) - MicroVM setup
- [DESKTOP.md](./DESKTOP.md) - Window manager specs
