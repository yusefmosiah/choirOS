# ChoirOS Event-Sourced Architecture

> NATS JetStream as the source of truth. Everything else is a projection.

---

## Core Principle

**The event stream is the filesystem.**

Every action—file create, file modify, component render, agent action, user undo—is an event in NATS JetStream. SQLite, the browser UI, and S3 backups are all *projections* of this stream. They don't sync with each other. They each derive from the single source of truth.

```
NATS JetStream (source of truth)
    │
    ├─→ SQLite (queryable projection)
    ├─→ Browser (rendered projection)  
    └─→ S3 (durable backup, periodic snapshots)
```

---

## Why This Architecture

### The Problem We're Solving

Agents write code at runtime. Sometimes it's bad. Users need instant undo. Traditional approaches:

- **Evaluate before applying**: Adds latency, kills the "live" feeling
- **Git-style commits**: Works for files, awkward for SQLite state
- **Prevent mistakes**: Impossible with generative code

### The Solution

Don't prevent mistakes. Make them cheap to reverse.

- Every change is an event
- Undo = publish a revert event
- All projections update automatically
- The timeline is the event log itself

---

## Two-Sandbox Model

Each user/agent pair gets two isolated environments:

### ChoirOS Sandbox (Long-lived)

- Runs the frontend (Vite + React)
- Maintains SQLite projection
- Serves UI to user's browser
- Subscribes to user's event stream
- Publishes user actions as events

### Agent Sandbox (Ephemeral, Firecracker)

- Spins up for compute tasks
- Subscribes to same event stream (read access)
- Publishes proposed changes as events
- Dies after task completion
- Hard isolation from ChoirOS sandbox

**The boundary is the event stream.** Agent doesn't touch ChoirOS directly. It publishes events. ChoirOS consumes them.

---

## Event Schema

### Base Event Structure

```typescript
interface ChoirOSEvent {
  id: string;                    // UUID
  stream_seq: number;            // JetStream sequence number
  timestamp: number;             // Unix ms
  user_id: string;
  source: 'user' | 'agent' | 'system';
  type: string;                  // Event type discriminator
  payload: Record<string, any>;
}
```

### File Events

```typescript
// File created or fully replaced
interface FileWriteEvent extends ChoirOSEvent {
  type: 'FILE_WRITE';
  payload: {
    path: string;               // Virtual path: /components/Header.tsx
    content: string;            // Full file content
    mime_type: string;
    hash: string;               // SHA-256 for dedup
  };
}

// File deleted
interface FileDeleteEvent extends ChoirOSEvent {
  type: 'FILE_DELETE';
  payload: {
    path: string;
  };
}

// File moved/renamed
interface FileMoveEvent extends ChoirOSEvent {
  type: 'FILE_MOVE';
  payload: {
    from_path: string;
    to_path: string;
  };
}
```

### Agent Events

```typescript
// Agent begins a task
interface AgentTaskStartEvent extends ChoirOSEvent {
  type: 'AGENT_TASK_START';
  source: 'agent';
  payload: {
    task_id: string;
    task_type: string;
    input: Record<string, any>;
  };
}

// Agent completes a task (groups related file events)
interface AgentTaskCompleteEvent extends ChoirOSEvent {
  type: 'AGENT_TASK_COMPLETE';
  source: 'agent';
  payload: {
    task_id: string;
    events_in_task: string[];   // IDs of events produced during this task
    summary: string;            // Human-readable description
  };
}
```

### User Events

```typescript
// User requests undo
interface UndoEvent extends ChoirOSEvent {
  type: 'UNDO';
  source: 'user';
  payload: {
    target_seq: number;         // Revert to state at this sequence number
    reason?: string;            // Optional feedback for agent
  };
}

// User accepts current state (optional, for feedback)
interface AcceptEvent extends ChoirOSEvent {
  type: 'ACCEPT';
  source: 'user';
  payload: {
    task_id?: string;           // Which agent task they're accepting
  };
}
```

### UI Events

```typescript
// Component render failed
interface RenderErrorEvent extends ChoirOSEvent {
  type: 'RENDER_ERROR';
  source: 'system';
  payload: {
    path: string;               // Which file caused it
    error: string;              // Error message
    stack?: string;
  };
}

// Component render succeeded
interface RenderSuccessEvent extends ChoirOSEvent {
  type: 'RENDER_SUCCESS';
  source: 'system';
  payload: {
    path: string;
  };
}
```

---

## NATS JetStream Configuration

### Stream Setup

```bash
# One stream per user - contains all their events
nats stream add CHOIROS_USER_{user_id} \
  --subjects "choiros.{user_id}.>" \
  --retention limits \
  --max-age 0 \              # Keep forever (this is the source of truth)
  --storage file \
  --replicas 3
```

### Subject Hierarchy

```
choiros.{user_id}.
├── file.write              # FILE_WRITE events
├── file.delete             # FILE_DELETE events
├── file.move               # FILE_MOVE events
├── agent.task.start        # AGENT_TASK_START
├── agent.task.complete     # AGENT_TASK_COMPLETE
├── user.undo               # UNDO events
├── user.accept             # ACCEPT events
├── system.render.error     # RENDER_ERROR
└── system.render.success   # RENDER_SUCCESS
```

### Consumers

```bash
# ChoirOS sandbox consumer - gets everything, persistent
nats consumer add CHOIROS_USER_{user_id} CHOIROS_SANDBOX \
  --filter "choiros.{user_id}.>" \
  --deliver all \
  --ack explicit \
  --replay instant

# Agent consumer - ephemeral, created per-task
# Starts from specific sequence or "last" depending on task needs
```

---

## SQLite as Projection

SQLite is a **materialized view** of the event stream. It exists for fast queries, not as source of truth.

### Schema

```sql
-- Current state of all files
CREATE TABLE files (
  path TEXT PRIMARY KEY,
  content TEXT,
  mime_type TEXT,
  hash TEXT,
  last_event_seq INTEGER,       -- Which event last modified this
  updated_at INTEGER
);

-- Index for fast path lookups
CREATE INDEX idx_files_path ON files(path);

-- Projection metadata
CREATE TABLE projection_state (
  key TEXT PRIMARY KEY,
  value TEXT
);

-- Track: last processed event sequence
-- INSERT INTO projection_state VALUES ('last_seq', '0');
```

### Projection Logic (Pseudocode)

```typescript
async function processEvent(event: ChoirOSEvent) {
  switch (event.type) {
    case 'FILE_WRITE':
      await db.run(`
        INSERT OR REPLACE INTO files (path, content, mime_type, hash, last_event_seq, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
      `, [event.payload.path, event.payload.content, event.payload.mime_type, 
          event.payload.hash, event.stream_seq, event.timestamp]);
      break;

    case 'FILE_DELETE':
      await db.run(`DELETE FROM files WHERE path = ?`, [event.payload.path]);
      break;

    case 'FILE_MOVE':
      await db.run(`UPDATE files SET path = ? WHERE path = ?`, 
        [event.payload.to_path, event.payload.from_path]);
      break;

    case 'UNDO':
      await rebuildFromSequence(event.payload.target_seq);
      break;
  }

  // Update projection checkpoint
  await db.run(`UPDATE projection_state SET value = ? WHERE key = 'last_seq'`, 
    [event.stream_seq]);
}
```

### Rebuild on Undo

```typescript
async function rebuildFromSequence(targetSeq: number) {
  // Clear current state
  await db.run(`DELETE FROM files`);
  
  // Replay events from beginning up to target
  const events = await nats.getEvents({ 
    stream: `CHOIROS_USER_${userId}`,
    startSeq: 1,
    endSeq: targetSeq 
  });

  for (const event of events) {
    if (event.type !== 'UNDO') {  // Don't replay undo events
      await processEvent(event);
    }
  }
}
```

### Snapshots for Performance

Rebuilding from event 0 is slow. Cache periodic snapshots:

```typescript
// Every N events, snapshot the SQLite file
async function maybeSnapshot(currentSeq: number) {
  const SNAPSHOT_INTERVAL = 100;
  
  if (currentSeq % SNAPSHOT_INTERVAL === 0) {
    const snapshot = await db.serialize();  // Get SQLite bytes
    await s3.put(`snapshots/${userId}/${currentSeq}.sqlite`, snapshot);
  }
}

// Rebuild using nearest snapshot
async function rebuildFromSequence(targetSeq: number) {
  // Find nearest snapshot before target
  const snapshotSeq = Math.floor(targetSeq / 100) * 100;
  
  if (snapshotSeq > 0) {
    const snapshot = await s3.get(`snapshots/${userId}/${snapshotSeq}.sqlite`);
    await db.restore(snapshot);
  } else {
    await db.run(`DELETE FROM files`);
  }

  // Replay only events after snapshot
  const events = await nats.getEvents({
    startSeq: snapshotSeq + 1,
    endSeq: targetSeq
  });

  for (const event of events) {
    await processEvent(event);
  }
}
```

---

## Browser Hot Reload Integration

The browser is another projection. When file events arrive, Vite HMR updates the view.

### ChoirOS Sandbox Watcher

```typescript
// Watch for file events, write to disk for Vite to pick up
nats.subscribe(`choiros.${userId}.file.*`, async (event) => {
  switch (event.type) {
    case 'FILE_WRITE':
      await fs.writeFile(
        path.join(WORKSPACE_DIR, event.payload.path),
        event.payload.content
      );
      // Vite HMR detects change, hot reloads
      break;

    case 'FILE_DELETE':
      await fs.unlink(path.join(WORKSPACE_DIR, event.payload.path));
      break;
  }
});
```

### Error Boundary Feedback

```tsx
// React error boundary publishes render errors back to stream
class ComponentErrorBoundary extends React.Component {
  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Publish error event
    nats.publish(`choiros.${userId}.system.render.error`, {
      type: 'RENDER_ERROR',
      source: 'system',
      payload: {
        path: this.props.componentPath,
        error: error.message,
        stack: error.stack
      }
    });
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback path={this.props.componentPath} />;
    }
    return this.props.children;
  }
}
```

### Agent Receives Feedback

```typescript
// Agent subscribes to render results
nats.subscribe(`choiros.${userId}.system.render.*`, (event) => {
  if (event.type === 'RENDER_ERROR') {
    // Add to agent context for next iteration
    agentContext.addError({
      file: event.payload.path,
      error: event.payload.error
    });
    // Agent can now fix the error
  }
});
```

---

## Undo Flow

User clicks undo. What happens:

```
1. User clicks "Undo" in UI
   │
2. UI publishes UNDO event to NATS
   │  { type: 'UNDO', payload: { target_seq: 1847 } }
   │
3. ChoirOS sandbox receives UNDO event
   │
4. SQLite projection rebuilds from target sequence
   │  - Load nearest snapshot
   │  - Replay events up to target_seq
   │
5. Files on disk updated to match rebuilt state
   │
6. Vite HMR triggers, browser updates
   │
7. Agent inbox receives UNDO event
   │  - Knows its last change was rejected
   │  - Gets user feedback if provided
```

Total latency: snapshot load + event replay + HMR. Should be sub-second for typical undo.

---

## Agent Workflow

### Writing Code

```typescript
// Agent wants to modify a component
async function agentModifyComponent(path: string, newContent: string) {
  // Publish task start
  await nats.publish(`choiros.${userId}.agent.task.start`, {
    type: 'AGENT_TASK_START',
    source: 'agent',
    payload: {
      task_id: uuid(),
      task_type: 'MODIFY_COMPONENT',
      input: { path }
    }
  });

  // Publish file write
  const writeEventId = uuid();
  await nats.publish(`choiros.${userId}.file.write`, {
    id: writeEventId,
    type: 'FILE_WRITE',
    source: 'agent',
    payload: {
      path,
      content: newContent,
      mime_type: 'text/typescript',
      hash: sha256(newContent)
    }
  });

  // Publish task complete
  await nats.publish(`choiros.${userId}.agent.task.complete`, {
    type: 'AGENT_TASK_COMPLETE',
    source: 'agent',
    payload: {
      task_id,
      events_in_task: [writeEventId],
      summary: `Modified ${path}`
    }
  });
}
```

### Receiving Feedback

```typescript
// Agent listens for results
nats.subscribe(`choiros.${userId}.system.render.*`, handleRenderResult);
nats.subscribe(`choiros.${userId}.user.undo`, handleUndo);
nats.subscribe(`choiros.${userId}.user.accept`, handleAccept);

function handleUndo(event: UndoEvent) {
  // User rejected our change
  const reason = event.payload.reason || 'User pressed undo';
  agentContext.addFeedback({
    type: 'rejection',
    reason,
    task_id: currentTaskId
  });
  // Adjust approach for next attempt
}

function handleAccept(event: AcceptEvent) {
  // User liked it - reinforce this pattern
  agentContext.addFeedback({
    type: 'acceptance',
    task_id: event.payload.task_id
  });
}
```

---

## Timeline UI

The event stream enables a visual timeline:

```typescript
// Fetch recent events for timeline display
async function getTimeline(limit: number = 50) {
  const events = await nats.getEvents({
    stream: `CHOIROS_USER_${userId}`,
    last: limit
  });

  return events
    .filter(e => e.type === 'AGENT_TASK_COMPLETE' || e.type === 'UNDO')
    .map(e => ({
      seq: e.stream_seq,
      timestamp: e.timestamp,
      summary: e.payload.summary || `Undo to ${e.payload.target_seq}`,
      source: e.source,
      canRevertTo: true
    }));
}
```

User sees a timeline of agent actions. Click any point to revert to that state.

---

## Startup / Recovery

When ChoirOS sandbox starts:

```typescript
async function initializeProjection() {
  // 1. Check for existing projection
  const lastSeq = await db.get(`SELECT value FROM projection_state WHERE key = 'last_seq'`);

  if (!lastSeq) {
    // Fresh start - replay from beginning (or latest snapshot)
    await rebuildFromSequence(Infinity);  // Infinity = current head
  } else {
    // Catch up from where we left off
    const events = await nats.getEvents({
      stream: `CHOIROS_USER_${userId}`,
      startSeq: parseInt(lastSeq.value) + 1
    });

    for (const event of events) {
      await processEvent(event);
    }
  }

  // 2. Subscribe to live events
  nats.subscribe(`choiros.${userId}.>`, processEvent);
}
```

---

## Key Insights

### Infrastructure as Data, Not Code

Kelsey Hightower's point: Kubernetes moved us from infrastructure-as-code to infrastructure-as-data. This architecture continues that trajectory. The event stream *is* the infrastructure. Code is just content that lives in the stream.

### Mistakes Are Cheap

We don't prevent bad code. We make reverting instant. The agent iterates at HMR speed. The user has one-click undo. The feedback loop is tight.

### The Agent Learns from the Stream

Every undo is training signal. Every accept is reinforcement. The event stream is both the filesystem and the feedback mechanism.

### Projections Are Disposable

SQLite can be rebuilt from scratch. Browser state can be rebuilt from scratch. Only the NATS stream is sacred. This makes the system resilient and portable.

---

## What to Build

1. **NATS stream setup** - One stream per user, subjects as specified
2. **Event publishing** - Functions to emit each event type
3. **SQLite projection** - Event processor that maintains file state
4. **Snapshot system** - Periodic SQLite snapshots to S3
5. **Undo handler** - Rebuild projection from target sequence
6. **File watcher bridge** - Write events to disk for Vite HMR
7. **Error boundary** - Publish render errors back to stream
8. **Timeline UI** - Visual history with click-to-revert
9. **Agent integration** - Subscribe to feedback events

Start with #1-3. Get events flowing and SQLite updating. The rest builds on that foundation.
