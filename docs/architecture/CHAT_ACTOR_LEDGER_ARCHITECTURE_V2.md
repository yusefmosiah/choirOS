# Chat-Actor-Ledger Architecture V2

**Status**: IMPLEMENTATION READY  
**Date**: 2026-01-30  
**Decisions**: FINAL

---

## Executive Summary

ChoirOS is redesigned around three core primitives:

1. **Per-Session Actors** (Ray-based): Each user session gets isolated, stateful actor instances that can be replayed, debugged, and hibernated
2. **Durable Ledger** (libsql/Turso): Append-only event log is the single source of truth—no NATS, no message bus
3. **Knowledge Graph** (ledger projection): Semantic visualization of what informed each run, constructed deterministically from ledger events

This is a clean break from the NATS event system. The new architecture treats **Chat as the control plane**, **programs as actors**, and **the ledger as the filesystem**.

---

## Core Concepts

### 1. Chat Hub (Control Plane)

The Chat app is the universal entry point:
- Receives all user prompts
- Routes work to appropriate actors
- Maintains session context
- Validates JWT authentication
- Coordinates multi-actor workflows

**Key insight**: Chat is not just another app—it's the orchestrator.

### 2. Program Actors (Per-Session)

Each program is a stateful Ray actor:

```
User Alice, Session 1 (Laptop Tab 1):
  ├── WriterActor-S1
  ├── MailActor-S1
  └── TerminalActor-S1

User Alice, Session 2 (Phone):
  ├── WriterActor-S2
  ├── MailActor-S2
  └── TerminalActor-S2
```

**Actor properties:**
- **Isolated**: Session A cannot corrupt Session B
- **Stateful**: Maintains cursor position, undo history, UI state
- **Stream-capable**: Emits tokens, tool calls, progress updates
- **Ledger-aware**: Writes all actions to durable ledger
- **Hibernatable**: Can snapshot to DB, restore later

**Why per-session vs per-user?**
- Replayability: Can replay Session A without affecting Session B
- Debugging: Clear isolation of "what happened in this tab"
- Failure containment: Actor crash kills one session, not all
- Concurrency: No message interleaving complexity

### 3. Tool Ledger (Single Source of Truth)

Append-only event log stored in libsql/Turso:

```sql
-- Core ledger table
ledger_events(
    id INTEGER PRIMARY KEY,
    run_id TEXT,
    session_id TEXT,
    actor_id TEXT,
    seq INTEGER,  -- Strict ordering within run
    type TEXT,    -- Event type
    payload_json TEXT,
    created_at TIMESTAMP
)
```

**Event types:**
- `chat.prompt` - User submits prompt
- `actor.call` - Actor method invoked
- `actor.stream.token` - Streaming token output
- `actor.stream.tool_call` - Tool call initiated
- `tool.result` - Tool execution result
- `file.read` - File loaded into context
- `file.write` - File modified
- `actor.state.snapshot` - Actor state checkpoint
- `run.complete` - Run finished

**Key principle**: Everything that happens is recorded. The ledger is the source of truth for replay, debugging, and the knowledge graph.

### 4. Knowledge Graph (Ledger Projection)

Not a separate system—derived view from ledger:

```
T=seq1:  [Intent: "Refactor auth"]

T=seq5:  [Intent]
         ├─ Source Code
         │  └─ auth.ts (discovered)
         └─ Research
            └─ search: "JWT patterns"

T=seq12: [Intent]
         ├─ Source Code
         │  ├─ auth.ts ✓ (loaded, lines 45-89)
         │  └─ middleware.ts ✓ (loaded)
         ├─ Research
         │  ├─ search: "JWT patterns"
         │  └─ search: "bcrypt best practices"
         └─ Standards
            └─ RFC 7519 (fetched)
```

**Features:**
- **Time-replayable**: View graph at any point in run (drag slider to seq=50)
- **Semantic categories**: Auto-discovered (Source Code, Documentation, Research)
- **Drill-down**: Click category → see files → see line ranges → see ledger events
- **Live updates**: Watch graph grow as run progresses

### 5. Resource Bus (Cross-Session Sync)

Ray actor singleton that enables collaboration:

```
Session 1 ──┐
            ├──► ResourceBus ◄──┐
Session 2 ──┘                   │
                        ┌───────┴───────┐
                        ▼               ▼
                   FileResource    MailResource
                   (CRDT-backed)   (CRDT-backed)
```

**How sync works:**
1. Session 1 edits file → publishes to ResourceBus
2. ResourceBus applies to CRDT (conflict resolution)
3. ResourceBus fans out to Session 2 (and other sessions)
4. Session 2 applies remote edit to local actor state

**Why this works:**
- Actors stay isolated (no direct actor-to-actor calls)
- Shared resources provide eventual consistency
- CRDTs handle simultaneous edits automatically
- Each session maintains its own cursor/undo state

---

## System Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        User Layer                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Tab 1     │  │   Tab 2     │  │   Phone     │         │
│  │ (Session 1) │  │ (Session 2) │  │ (Session 3) │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
└─────────┼────────────────┼────────────────┼─────────────────┘
          │                │                │
          └────────────────┴────────────────┘
                           │
                    ┌──────▼──────┐
                    │  Chat Hub   │
                    │  (Router)   │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌─────────────────┐ ┌──────────────┐ ┌──────────────┐
│  Actor Runtime  │ │   Ledger     │ │  Knowledge   │
│  (Ray cluster)  │ │  (libsql)    │ │   Graph      │
│                 │ │              │ │ Projection   │
│ • WriterActor   │ │ • Events     │ │              │
│ • MailActor     │ │ • Snapshots  │ │ • Build from │
│ • TerminalActor │ │ • Token      │ │   ledger     │
│                 │ │   streams    │ │ • Time-travel│
└────────┬────────┘ └──────────────┘ └──────────────┘
         │
         ▼
┌─────────────────┐
│  Resource Bus   │
│  (Ray singleton)│
│                 │
│ • FileResource  │
│ • MailResource  │
│ • CRDT sync     │
└─────────────────┘
```

### Data Flow: Prompt → Result

**Step 1: Prompt Submission**
```
User (Tab 1) → ChatHub
ChatHub validates JWT
ChatHub assigns run_id, session_id
ChatHub logs: ledger.append({type: "chat.prompt", ...})
```

**Step 2: Actor Selection & Call**
```
ChatHub analyzes prompt → selects WriterActor
ChatHub calls: WriterActor.process_prompt.remote(prompt, run_id)
Ledger logs: {type: "actor.call", actor_id: "WriterActor", ...}
```

**Step 3: Actor Execution**
```
WriterActor:
  1. Opens file via ResourceBus (subscribes to updates)
  2. Reads context files
  3. Streams tokens to ChatHub
  4. Calls tools (SearchActor, ReaderActor)
  5. Each action logged to ledger
```

**Step 4: Cross-Session Sync**
```
WriterActor-S1 edits file → ResourceBus
ResourceBus:
  - Applies to CRDT
  - Persists to storage
  - Fans out to WriterActor-S2, WriterActor-S3
WriterActor-S2 updates local state → UI updates
```

**Step 5: Knowledge Graph Updates**
```
KnowledgeGraphProjection:
  - Consumes ledger events
  - Builds graph incrementally
  - Emits deltas to UI
  - User watches graph grow live
```

**Step 6: Completion**
```
WriterActor finishes → returns result
ChatHub logs: {type: "run.complete", ...}
ChatHub returns result to User
```

---

## Database Schema

### 1. Ledger Events (Core)

```sql
CREATE TABLE ledger_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    actor_id TEXT,
    seq INTEGER NOT NULL,  -- Monotonic within run
    type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(run_id, seq)
);

CREATE INDEX idx_ledger_run_seq ON ledger_events(run_id, seq);
CREATE INDEX idx_ledger_session ON ledger_events(session_id);
CREATE INDEX idx_ledger_type ON ledger_events(type);
```

### 2. Actor Snapshots

```sql
CREATE TABLE actor_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    seq_from INTEGER,  -- First event this snapshot covers
    seq_to INTEGER,    -- Last event (snapshot point)
    state_json TEXT NOT NULL,  -- Serialized actor state
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_snapshots_session_actor ON actor_snapshots(session_id, actor_id)
);
```

### 3. Token Streams (Compressed)

```sql
CREATE TABLE token_streams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    content_compressed BLOB NOT NULL,  -- zstd compressed
    tokens_count INTEGER,
    first_seq INTEGER,  -- Links to ledger
    last_seq INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_compacted BOOLEAN DEFAULT FALSE,
    
    INDEX idx_tokens_run ON token_streams(run_id)
);

-- Hot tokens (recent, uncompressed)
CREATE TABLE token_streams_hot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    token TEXT NOT NULL,
    seq INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4. Knowledge Graph (Projection Cache)

```sql
-- Nodes (reconstructed from ledger, cached for speed)
CREATE TABLE knowledge_nodes (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    created_at_seq INTEGER NOT NULL,
    node_type TEXT NOT NULL,  -- 'root_intent', 'category', 'source', 'output'
    
    -- Intent
    intent_text TEXT,
    
    -- Category
    category_name TEXT,
    parent_intent_id TEXT,
    
    -- Source
    source_type TEXT,  -- 'file', 'url', 'tool_result'
    source_uri TEXT,
    content_hash TEXT,
    line_ranges_json TEXT,
    content_preview TEXT,
    parent_category_id TEXT,
    discovery_seq INTEGER,
    loaded_seq INTEGER,
    
    -- Output
    output_uri TEXT,
    derived_from_sources_json TEXT,
    
    FOREIGN KEY (run_id) REFERENCES runs(id)
);

-- Edges
CREATE TABLE knowledge_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    from_node_id TEXT NOT NULL,
    to_node_id TEXT NOT NULL,
    edge_type TEXT NOT NULL,  -- 'produced', 'references', 'derived_from'
    created_at_seq INTEGER,
    strength REAL  -- 0-1 for similarity
);

-- Source usage in synthesis
CREATE TABLE source_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    referenced_at_seq INTEGER,
    context_snippet TEXT
);
```

### 5. Runs & Sessions

```sql
CREATE TABLE runs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    status TEXT,  -- 'running', 'complete', 'failed', 'hibernated'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    final_result_json TEXT
);

CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    status TEXT,  -- 'active', 'hibernated', 'closed'
    current_run_id TEXT,
    actor_snapshots_json TEXT,  -- Map of actor_id -> snapshot_id
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP,
    hibernated_at TIMESTAMP
);
```

---

## API Specification

### ChatHub API

```python
class ChatHub:
    async def create_session(self, user_id: str) -> Session:
        """Create new session with JWT validation"""
        pass
    
    async def submit_prompt(
        self, 
        session_id: str, 
        prompt: str,
        context: Optional[dict] = None
    ) -> RunResult:
        """Submit prompt, orchestrate actor execution"""
        pass
    
    async def stream_run(
        self,
        run_id: str
    ) -> AsyncIterator[StreamEvent]:
        """Stream tokens, tool calls, progress"""
        pass
    
    async def hibernate_session(self, session_id: str) -> Snapshot:
        """Snapshot all actors, kill them"""
        pass
    
    async def restore_session(self, session_id: str) -> Session:
        """Restore from hibernation"""
        pass
```

### Actor Interface

```python
@ray.remote
class WriterActor:
    def __init__(self, session_id: str, user_id: str, run_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.run_id = run_id
        self.resource_bus = ray.get_actor("resource_bus")
        self.ledger = ray.get_actor("ledger")
    
    async def process_prompt(self, prompt: str) -> Result:
        """Main entry point for ChatHub"""
        pass
    
    async def open_file(self, path: str) -> FileState:
        """Subscribe to file via ResourceBus"""
        pass
    
    async def edit_file(self, path: str, edit: Edit) -> None:
        """Edit file, publish to ResourceBus"""
        pass
    
    async def get_state(self) -> dict:
        """For snapshots"""
        pass
    
    async def restore_state(self, state: dict) -> None:
        """From hibernation"""
        pass
```

### ResourceBus API

```python
@ray.remote
class ResourceBus:
    async def subscribe(
        self, 
        resource_type: str, 
        resource_id: str,
        session_actor: ray.ObjectRef
    ) -> ResourceState:
        """Session actor subscribes to resource updates"""
        pass
    
    async def publish(
        self,
        resource_type: str,
        resource_id: str,
        operation: dict,
        sender_session: ray.ObjectRef
    ) -> None:
        """Fan out to all subscribers except sender"""
        pass
    
    async def get_resource(self, resource_type: str, resource_id: str) -> Resource:
        """Get or create resource actor"""
        pass
```

### KnowledgeGraph API

```python
@ray.remote
class KnowledgeGraphProjection:
    async def replay(self, run_id: str, up_to_seq: Optional[int] = None) -> Graph:
        """Build graph from ledger events"""
        pass
    
    async def subscribe_live(
        self, 
        run_id: str,
        ui_actor: ray.ObjectRef
    ) -> None:
        """Stream graph deltas as run progresses"""
        pass
    
    async def get_delta_since(self, run_id: str, seq: int) -> GraphDelta:
        """Incremental update"""
        pass
```

---

## Implementation Phases (Test-Driven)

### Phase 1: Core Actor Runtime (Week 1)

**Goal**: Ray actors can be created, called, and destroyed

**The One Test:**
```python
def test_actor_lifecycle():
    """PREDICTION: Creating an actor, calling a method, and killing it works"""
    actor = ray.remote(EchoActor).remote()
    result = ray.get(actor.echo.remote("hello"))
    assert result == "hello"
    ray.kill(actor)
    # OBSERVE: No exceptions, clean shutdown
```

**Implementation:**
- Setup Ray cluster (local for dev)
- Create base Actor class
- Implement lifecycle methods

---

### Phase 2: Ledger Append (Week 1)

**Goal**: Events append to DB and can be queried by seq

**The One Test:**
```python
async def test_ledger_append_and_query():
    """PREDICTION: Events written to ledger can be retrieved in order"""
    ledger = Ledger(db_path=":memory:")
    
    seq1 = await ledger.append(run_id="r1", type="test", payload={"data": "a"})
    seq2 = await ledger.append(run_id="r1", type="test", payload={"data": "b"})
    
    events = await ledger.query(run_id="r1", seq_from=seq1, seq_to=seq2)
    assert len(events) == 2
    assert events[0].payload["data"] == "a"
    assert events[1].seq == seq2
    # OBSERVE: Strict ordering, no gaps
```

**Implementation:**
- Setup libsql/Turso
- Implement Ledger actor
- Event serialization/deserialization

---

### Phase 3: Per-Session Actor + Ledger (Week 2)

**Goal**: Session creates actor, actor writes to ledger

**The One Test:**
```python
async def test_actor_writes_to_ledger():
    """PREDICTION: Actor execution produces traceable events"""
    session = Session.create("user-123")
    actor = session.create_actor(WriterActor)
    
    result = await actor.write_file.remote("/test.txt", "hello")
    
    events = await ledger.query(run_id=session.run_id)
    assert any(e.type == "file.write" for e in events)
    assert any(e.type == "actor.call" for e in events)
    # OBSERVE: Complete trace in ledger
```

**Implementation:**
- Session manager
- Actor base class with ledger integration
- Basic WriterActor implementation

---

### Phase 4: Resource Bus + Cross-Session Sync (Week 2-3)

**Goal**: Two sessions see same file updates

**The One Test:**
```python
async def test_cross_session_file_sync():
    """PREDICTION: File edit in Session A appears in Session B within 1s"""
    session_a = Session.create("user-123", "tab-1")
    session_b = Session.create("user-123", "tab-2")
    
    await session_a.actor.open_file.remote("/shared.txt")
    await session_b.actor.open_file.remote("/shared.txt")
    
    await session_a.actor.edit.remote("new content")
    await asyncio.sleep(0.5)
    
    content_b = await session_b.actor.get_content.remote()
    assert content_b == "new content"
    # OBSERVE: Eventual consistency
```

**Implementation:**
- ResourceBus actor
- FileResource with Yjs CRDT
- Subscribe/publish protocol

---

### Phase 5: Knowledge Graph Projection (Week 3-4)

**Goal**: Graph built from ledger, shows sources at any seq

**The One Test:**
```python
async def test_knowledge_graph_replay():
    """PREDICTION: Replaying events reconstructs exact graph at any point"""
    # Populate ledger with events
    run_id = "test-run"
    for i in range(100):
        await ledger.append(run_id=run_id, seq=i, type="test", payload={})
    
    # Build graph at seq 50
    graph_at_50 = await KnowledgeGraphProjection.replay(run_id, seq=50)
    
    # Build graph at seq 100
    graph_at_100 = await KnowledgeGraphProjection.replay(run_id, seq=100)
    
    # Verify determinism
    graph_at_50_again = await KnowledgeGraphProjection.replay(run_id, seq=50)
    assert graph_at_50 == graph_at_50_again
    # OBSERVE: Same input → same output
```

**Implementation:**
- KnowledgeGraphProjection actor
- Event-to-node mapping
- Graph visualization data structure

---

### Phase 6: Hibernation (Week 4)

**Goal**: Idle actor snapshots, restores on wake

**The One Test:**
```python
async def test_actor_hibernation():
    """PREDICTION: Actor hibernates and restores with exact state"""
    actor = await create_actor(WriterActor)
    await actor.set_cursor.remote(42)
    await actor.set_content.remote("hello world")
    
    # Hibernate
    snapshot = await hibernate(actor)
    ray.kill(actor)
    
    # Restore
    new_actor = await restore(snapshot)
    assert await new_actor.get_cursor.remote() == 42
    assert await new_actor.get_content.remote() == "hello world"
    # OBSERVE: State preserved
```

**Implementation:**
- Snapshot serialization
- Hibernation scheduler (10min idle)
- Restore from snapshot

---

### Phase 7: Token Stream Storage (Week 4-5)

**Goal**: Tokens stored compressed, retrievable

**The One Test:**
```python
async def test_token_stream_retrieval():
    """PREDICTION: Token stream stored efficiently but fully retrievable"""
    run_id = "test-run"
    
    # Store 1000 tokens
    tokens = [f"token_{i} " for i in range(1000)]
    for token in tokens:
        await token_store.append(run_id, token)
    
    # Compact
    await token_store.compact(run_id)
    
    # Retrieve
    stream = await token_store.get_stream(run_id)
    assert len(stream.tokens) == 1000
    assert stream.compression_ratio > 5.0
    # OBSERVE: Data intact, storage efficient
```

**Implementation:**
- Token buffer (hot)
- Compression (zstd)
- Retrieval API

---

### Phase 8: ChatHub Integration (Week 5-6)

**Goal**: Full flow: prompt → result → graph

**The One Test:**
```python
async def test_end_to_end_chat_flow():
    """PREDICTION: User prompt flows through system, produces traceable result"""
    chat = ChatHub()
    session = await chat.create_session("user-123")
    
    result = await chat.submit_prompt(
        session_id=session.id,
        prompt="Write hello world in Python"
    )
    
    assert result.status == "complete"
    
    # Verify ledger
    events = await ledger.query(run_id=result.run_id)
    assert any(e.type == "chat.prompt" for e in events)
    assert any(e.type == "file.write" for e in events)
    
    # Verify graph
    graph = await KnowledgeGraphProjection.get_graph(result.run_id)
    assert len(graph.sources) > 0
    # OBSERVE: Complete traceability
```

**Implementation:**
- ChatHub orchestration
- Actor routing
- Error handling
- UI streaming

---

## Failure Handling

### Actor Crashes

**Detection**: Supervisor monitors actor health via Ray

**Recovery**:
1. Detect crash (Ray actor dead)
2. Fetch last snapshot from ledger
3. Create new actor with same session_id
4. Restore state from snapshot
5. Replay events from snapshot.seq to current
6. Continue run

**User experience**: Brief "Reconnecting..." message, then continue

### Ledger Failures

**Write failure**: 
- Buffer in memory
- Retry with exponential backoff
- If persists: fail the run, notify user

**Read failure**:
- Use replica (Turso has built-in replication)
- If unavailable: degraded mode (continue without replay)

### Resource Bus Failures

**Bus crash**: 
- All sync stops temporarily
- Sessions fall back to local-only mode
- Auto-restart bus
- Reconnect sessions

### Network Partitions

**Session loses connection**:
- Actor continues running (async)
- Reconnect: fetch missed events from ledger
- Replay deltas to catch up UI

**Long partition (> 5 min)**:
- Hibernate session
- User returns: restore from snapshot

---

## Security Model

### Authentication

- JWT issued on login (Auth app)
- JWT contains: user_id, session_id, exp
- Validated by ChatHub on every request
- Short expiry (15 min), refresh token (7 days)

### Authorization

- User can only access own sessions
- Session isolation enforced by actor runtime
- ResourceBus validates session ownership before fan-out

### Data Isolation

- Ledger rows scoped to user_id + session_id
- Actor state never leaves Ray cluster
- Snapshots encrypted at rest (libsql encryption)

---

## Testing Strategy

### Unit Tests

One test per feature (as defined in phases)

### Integration Tests

```python
async def test_multi_session_collaboration():
    """Three sessions editing same file concurrently"""
    pass

async def test_replay_after_actor_crash():
    """Kill actor mid-run, verify replay reconstructs state"""
    pass

async def test_hibernation_under_load():
    """100 sessions, hibernate half, verify restore works"""
    pass
```

### E2E Tests

```python
async def test_full_user_workflow():
    """
    1. User opens Choir in two tabs
    2. Opens same file in both
    3. Edits in Tab 1
    4. Verifies sync in Tab 2
    5. Closes Tab 1 (hibernate)
    6. Reopens Tab 1 (restore)
    7. Continues editing
    """
    pass
```

---

## Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Actor runtime** | Ray | Python-native, distributed, proven |
| **Ledger DB** | libsql/Turso | SQLite-compatible, distributed, edge-ready |
| **CRDT** | Yjs (via WASM) | Proven text CRDT, good conflict resolution |
| **WebSocket** | FastAPI + python-socketio | Bidirectional, widely supported |
| **Compression** | zstd | Fast, good ratio, streamable |
| **Serialization** | msgspec | Fast JSON, schema validation |

---

## Success Criteria

1. ✅ ChatHub can route prompts to any actor
2. ✅ Actors stream tokens and tool calls live to UI
3. ✅ Ledger captures all events with strict ordering
4. ✅ Knowledge graph reconstructs deterministically from ledger
5. ✅ Cross-session sync works (edit in Tab 1 appears in Tab 2)
6. ✅ Hibernation preserves exact actor state
7. ✅ Token streams compressed 5x+ but fully retrievable
8. ✅ Actor crash recovery replays from snapshot
9. ✅ Full replay: can reconstruct any run from ledger alone

---

## Next Steps

1. **Setup development environment**
   - Install Ray, libsql client
   - Setup Yjs WASM bridge
   - Create test harness

2. **Begin Phase 1**
   - Implement EchoActor
   - Write `test_actor_lifecycle`
   - Make it pass

3. **Iterate through phases**
   - One phase per week
   - One test per feature
   - Green before moving on

---

## Appendix: Ray Actor Pattern

```python
import ray
import asyncio

@ray.remote
class BaseActor:
    """Template for all ChoirOS actors"""
    
    def __init__(self, session_id: str, user_id: str, run_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.run_id = run_id
        self.created_at = time.time()
        
        # Connect to system actors
        self.ledger = ray.get_actor("ledger")
        self.resource_bus = ray.get_actor("resource_bus")
    
    async def log_event(self, type: str, payload: dict):
        """Write to ledger"""
        await self.ledger.append.remote(
            run_id=self.run_id,
            session_id=self.session_id,
            actor_id=self.__class__.__name__,
            type=type,
            payload=payload
        )
    
    async def get_state(self) -> dict:
        """Override in subclass"""
        return {
            "session_id": self.session_id,
            "actor_type": self.__class__.__name__,
            "created_at": self.created_at
        }
    
    async def restore_state(self, state: dict):
        """Override in subclass"""
        pass


# Example: WriterActor
@ray.remote
class WriterActor(BaseActor):
    def __init__(self, session_id: str, user_id: str, run_id: str):
        super().__init__(session_id, user_id, run_id)
        self.cursor_position = 0
        self.open_files = {}
    
    async def open_file(self, path: str):
        # Subscribe via ResourceBus
        state = await self.resource_bus.subscribe.remote(
            resource_type="file",
            resource_id=path,
            session_actor=ray.get_actor(f"writer_actor_{self.session_id}")
        )
        self.open_files[path] = state
        await self.log_event("file.open", {"path": path})
    
    async def edit_file(self, path: str, edit: dict):
        # Apply locally
        self.open_files[path].apply(edit)
        self.cursor_position = edit.get("new_cursor", self.cursor_position)
        
        # Publish to ResourceBus
        await self.resource_bus.publish.remote(
            resource_type="file",
            resource_id=path,
            operation=edit,
            sender_session=ray.get_actor(f"writer_actor_{self.session_id}")
        )
        
        await self.log_event("file.edit", {"path": path, "edit": edit})
    
    async def get_state(self):
        base = await super().get_state()
        base.update({
            "cursor_position": self.cursor_position,
            "open_files": list(self.open_files.keys())
        })
        return base
    
    async def restore_state(self, state: dict):
        self.cursor_position = state["cursor_position"]
        # Re-open files (will re-subscribe to ResourceBus)
        for path in state["open_files"]:
            await self.open_file(path)
```

---

*This architecture is ready for implementation. Start with Phase 1 test.*
