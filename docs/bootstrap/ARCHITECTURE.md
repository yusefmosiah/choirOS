# ChoirOS Architecture

> A distributed web desktop that appears local but runs in a sandbox.

## The Paradigm: Sandbox-First

> **"The shell runs inside the agent sandbox."**

The browser is a **thin client**. The Choir desktop (Vite + React app) runs inside a microVM, not in the browser. This enables:
- Vibecoding: agents modify shell files → Vite HMR → browser updates live
- Security: arbitrary code runs in VM, not browser
- Composability: building Choir in Choir is possible

## Core Principles

1. **Thin client, smart sandbox** - Browser renders, VM computes
2. **Per-user sovereign data** - Each user has their own SQLite synced to S3
3. **NATS as the nervous system** - All events flow through a global log stream
4. **Isolated agents** - Every agent runs in a Firecracker microVM
5. **UX over prompts** - Users shouldn't need to prompt engineer
6. **Collaborative Caching (Thought Bank)** - Agents publish artifacts, receive micropayments on citation

---

## System Overview

```
┌─────────────────────────────────────────────┐
│           Browser (Thin Client)                  │
│     WebSocket only — no app logic here           │
└──────────────────────┬──────────────────────┘
                       │ WebSocket
                       ▼
┌─────────────────────────────────────────────┐
│      User’s MicroVM (Firecracker)                 │
│  ┌─────────────────────────────────────────┐  │
│  │ /app (Choir shell source, Vite project)  │  │
│  │    ├── Vite dev server (serves UI)        │  │
│  │    ├── HMR WebSocket (live updates)       │  │
│  │    └── Agent can modify any file here     │  │
│  ├─────────────────────────────────────────┤  │
│  │ /artifacts (user content, theme, config)│  │
│  ├─────────────────────────────────────────┤  │
│  │ /state (SQLite, action log)             │  │
│  ├─────────────────────────────────────────┤  │
│  │ Agent runtime (→ receives ? bar input)   │  │
│  └─────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────┘
                       │ NATS
                       ▼
┌─────────────────────────────────────────────┐
│           Global Infrastructure                  │
│  ┌───────────┐ ┌───────────┐ ┌─────────────┐  │
│  │    NATS   │ │     S3    │ │   Qdrant    │  │
│  │ JetStream │ │ (per-user)│ │  (vectors)  │  │
│  └───────────┘ └───────────┘ └─────────────┘  │
└─────────────────────────────────────────────┘
```
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

### MicroVM (where the shell runs)

| Component | Responsibility |
|-----------|----------------|
| **Vite dev server** | Serves UI to browser, HMR for live updates |
| **Agent runtime** | Receives ? bar input, reads/writes files |
| **Shell source** | Full Choir React app, modifiable by agent |
| **Artifacts** | User content, theme, app configs |
| **SQLite** | Local state, action log |

### Browser (thin client)

| Component | Responsibility |
|-----------|----------------|
| **WebSocket** | Connects to VM's Vite server |
| **Rendering** | Displays whatever Vite serves |
| **Input** | Captures user actions, sends to VM |

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
