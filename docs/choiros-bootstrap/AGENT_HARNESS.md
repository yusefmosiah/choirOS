# Agent Harness Architecture

> Distributed agency with live NATS I/O.

---

## Core Insight

**Agents are continuous NATS subscribers, not request/response endpoints.**

While an agent is blocked on an LLM call (10-60+ seconds), its inbox accumulates events:
- Citations from other agents
- Priority changes from orchestrator
- Context updates from memory layer

When the LLM returns, the agent checks its inbox and **adapts live**.

---

## Architecture

```
                                   NATS JetStream
                                        │
         ┌──────────────────────────────┼──────────────────────────────┐
         │                              │                              │
         ▼                              ▼                              ▼
  ┌─────────────┐               ┌─────────────┐               ┌─────────────┐
  │   Agent A   │               │   Agent B   │               │   Agent C   │
  │  (Claude)   │               │  (GPT-4)    │               │  (Gemini)   │
  ├─────────────┤               ├─────────────┤               ├─────────────┤
  │  Inbox      │◄──────────────│  Outbox     │               │             │
  │  (sub)      │   citation    │  (pub)      │               │             │
  └─────────────┘               └─────────────┘               └─────────────┘
```

Key principles:
1. **One LLM per agent** - prompt caching coherence
2. **Composition of agents** - cost/latency optimization via routing
3. **NATS as I/O** - not just event bus, but the communication layer
4. **Each agent in Firecracker** - shared sandbox, isolated execution
5. **Global namespace** - all agents communicate in one shared workspace

### Global Agent Namespace

All agents exist in **one global namespace**, not isolated per-user. Your agents and my agents communicate directly through the same NATS subjects.

```
┌────────────────────────────────────────────────┐
│              NATS Global Namespace              │
│                                                 │
│  Agent A ←→ Agent B ←→ Agent C ←→ Agent D      │
│  (user X)   (user X)   (user Y)   (user Y)     │
│                                                 │
│  Cross-user citation, collaboration, discovery  │
└────────────────────────────────────────────────┘
```

- Agent IDs are globally unique, not scoped by user
- User ownership is metadata, not namespace isolation
- My researcher can cite your researcher's prior art
- The "collective intelligence" emerges from all agents messaging freely
- Permissions control visibility, not architecture

---

## Agent Foliations

| Agent | Role | Subscribes | Publishes |
|-------|------|------------|-----------|
| **Researcher** | Does the work | `agent.{id}.inbox`, `tasks` | `results`, `citations` |
| **Goal Setter** | Orchestrates, delegates | `user.*.action.COMMAND`, `agent.*.status` | `priority`, `spawn` |
| **Context Manager** | Memory, retrieval | `context.requests.*` | `context.updates` |
| **Inbox Handler** | Interrupt triage | `agent.{parent}.inbox` | Routes to parent |

### Researcher (many instances)
- Spawns child researchers (recursive)
- Tools: `search_choir_kb`, `cite_article`, `publish_to_choir`, web search
- Emits citations when using other artifacts

### Goal Setter (superagent)
- Designs task decomposition
- Redefines priorities live based on intermediate results
- Uses most capable model

### Context Manager
- Non-LLM or lightweight LLM
- Serves context on demand
- Shared memory layer for all researchers

### Inbox Handler
- Buffers events during LLM blocking
- Decides: interrupt now? queue? escalate?
- Can be rule-based, no LLM needed

---

## Agent Lifecycle

```python
class Agent:
    async def run(self):
        # Subscribe to inbox
        await self.nats.subscribe(f"agent.{self.id}.inbox", self.on_inbox)
        await self.nats.subscribe(f"agent.{self.id}.tasks", self.on_task)

        while self.running:
            task = await self.task_queue.get()
            await self.execute_task(task)

    async def on_inbox(self, msg):
        """Events accumulate while we're blocked on LLM"""
        self.inbox.put_nowait(msg)

    async def execute_task(self, task):
        while not task.complete:
            # Check inbox BEFORE each LLM turn
            events = self.drain_inbox()
            self.adapt_context(events)

            # LLM call (blocks)
            response = await self.llm.complete(
                messages=self.context.messages,
                tools=self.tools
            )

            await self.handle_response(response)

    def adapt_context(self, events):
        for event in events:
            if event.type == 'CITATION_RECEIVED':
                self.context.inject_system_message(
                    f"[Update: Your work was cited by {event.citer}]"
                )
            elif event.type == 'PRIORITY_CHANGE':
                self.current_task.priority = event.priority
```

---

## Inter-Agent Communication Subjects

```
choiros.
├── agent.{agent_id}.
│   ├── inbox              # Incoming events (citations, priority, context)
│   ├── outbox             # Agent publishes here
│   ├── status             # running | blocked | complete
│   ├── spawn              # Spawn child agent
│   └── tasks              # New tasks for this agent
├── citation.
│   ├── created            # New citation recorded
│   └── notify.{agent_id}  # "You were cited" → goes to inbox
└── orchestrator.
    ├── priority           # Task priority updates
    └── context            # Context manager broadcasts
```

---

## Persistence: SQLite Virtual Filesystem

Decision: **SQLite** over persistent FS volumes.

| Benefit | Why |
|---------|-----|
| Single-file export | Matches "portable agentic computer" vision |
| Lower cost | No EBS volumes, just S3 + memory |
| Queryable state | Find artifacts by content, metadata |
| Simpler VM lifecycle | No mount/unmount choreography |

Trade-off: VFS abstraction layer so agents use normal file APIs:

```python
# Agent code (unchanged)
with open('/workspace/notes.md', 'w') as f:
    f.write(content)

# VFS layer translates to:
# INSERT INTO files (path, content) VALUES ('/workspace/notes.md', ...)
```

### Schema

```sql
CREATE TABLE files (
    path TEXT PRIMARY KEY,
    content BLOB,
    mime_type TEXT,
    hash TEXT,              -- SHA-256 for integrity
    created_at INTEGER,
    updated_at INTEGER
);

CREATE TABLE agent_state (
    key TEXT PRIMARY KEY,
    value JSON
);

CREATE TABLE inbox (
    id TEXT PRIMARY KEY,
    event_type TEXT,
    payload JSON,
    received_at INTEGER,
    processed_at INTEGER
);
```

---

## Ontology Mapping

Internal architecture is **generic and recursive**. UX is **declarative and deterministic**.

| Internal (Code) | External (UX) |
|-----------------|---------------|
| `Agent { role: "researcher" }` | "🔍 Researcher" |
| `Event { type: "CITED" }` | "Your article was cited!" |
| `spawn_child({ role: ... })` | "[Launching sub-researcher...]" |

Some agents are **UX-visible** (Researcher, Goal Setter), some are **infrastructure** (Inbox Handler, Context Manager).

```python
# Role definitions provide mapping
class AgentRole:
    name: str           # "researcher"
    display_name: str   # "Research Agent"
    icon: str           # "🔍"
    visible: bool       # True = show in UI
```

---

## Mail App Pattern

Every app becomes a chat app. The agent inbox manifests as:
- A **file on desktop** (notification)
- An **entry in mail app** (threaded view)

When your agent gets cited:
1. Citation event → `citation.notify.{your_agent_id}`
2. Your agent's inbox receives it
3. Persisted to SQLite inbox table
4. Synced to browser → appears in Mail app

---

## Next Steps

1. Implement minimal harness with NATS coupling
2. Create VFS layer for SQLite
3. Build Goal Setter with spawn capability
4. Setup NATS dev environment

See also:
- [NATS.md](./NATS.md) - Event bus configuration
- [FIRECRACKER.md](./FIRECRACKER.md) - VM isolation
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System overview
