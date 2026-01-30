# Collaborative Writing Implementation Runbook (Chat Hub)

**Date**: 2026-01-30
**Based on**: `docs/research/COLLABORATIVE_DOCUMENT_EDITING_RESEARCH.md`
**Context**: Chat is the control plane. Writer, Context Heatmap, Runmap, and Audit are projections over the same tool-call ledger.

**Architecture Notes**:
- **Chat Hub**: Default app with prompt bar and tool-call ledger timeline
- **Event Sourcing**: NATS JetStream (immutable source of truth)
- **Projection**: libsql (materialized state)
- **Real-time**: NATS WebSocket to browser
- **CRDT**: Deferred to Phase 5 (start with event-based edits)

---

## Phase 1: Tool-Call Ledger (Source of Truth)

### PREDICTION
All AI actions can be reconstructed from a tool-call ledger that is queryable by session and subscribed to by any app.

### EXPERIMENT

#### 1.1 Add Tool-Call and App Events to Event Contract

**File**: `supervisor/event_contract.py`

```python
# Add to CHOIR_EVENT_TYPES_V0
"chat.message.create",
"tool.call",
"tool.result",
"app.spawn",
"app.focus",
"app.view.sync",
```

**File**: `choiros/src/lib/event_contract.ts`

```typescript
export const CHOIR_EVENT_TYPES_V0 = [
    // ... existing events
    'chat.message.create',
    'tool.call',
    'tool.result',
    'app.spawn',
    'app.focus',
    'app.view.sync',
] as const;
```

#### 1.2 Add Tool-Call Projection Table

**File**: `supervisor/db.py`

Add to `_init_schema()`:

```python
CREATE TABLE IF NOT EXISTS tool_calls (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    tool_args JSON,
    tool_result JSON,
    source TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_calls_created ON tool_calls(created_at);
```

Add to `_materialize_projection()`:

```python
elif event_type == "tool.call":
    tool_call_id = payload.get("tool_call_id") or str(uuid.uuid4())
    self.conn.execute(
        """INSERT INTO tool_calls (id, session_id, tool_name, tool_args, source)
           VALUES (?, ?, ?, ?, ?)""",
        (
            tool_call_id,
            payload.get("session_id"),
            payload.get("tool"),
            json.dumps(payload.get("args", {})),
            event_source,
        ),
    )
elif event_type == "tool.result":
    tool_call_id = payload.get("tool_call_id")
    if tool_call_id:
        self.conn.execute(
            """UPDATE tool_calls SET tool_result = ? WHERE id = ?""",
            (json.dumps(payload.get("result", {})), tool_call_id),
        )
```

#### 1.3 Add Ledger API

**File**: `api/routers/ledger.py` (new file)

```python
"""Tool-call ledger API."""

from fastapi import APIRouter
from shared.auth import get_auth_store
from supervisor.db import get_store

router = APIRouter()

@router.get("/ledger/{session_id}")
async def get_ledger(session_id: str):
    session = get_auth_store().verify_session()
    user_id = session.user_id if session else "local"
    store = get_store(user_id)
    return {"tool_calls": store.list_tool_calls(session_id)}
```

**File**: `api/main.py`

```python
from api.routers import ledger
app.include_router(ledger.router, prefix="/api", tags=["ledger"])
```

### OBSERVE
- `tool.call` and `tool.result` events appear in NATS JetStream
- `tool_calls` table persists the call/response timeline by session
- `/api/ledger/{session_id}` returns the ledger in order

---

## Phase 2: Chat Hub UI (Default App)

### PREDICTION
The Chat app can show a tool-call timeline and act as the command center for spawning other apps.

### EXPERIMENT

#### 2.1 Tool-Call Timeline in Chat

**File**: `choiros/src/components/apps/Chat.tsx`

- Render a timeline of tool calls from `/api/ledger/{session_id}`
- Keep the message list as an optional view, not the primary context model

#### 2.2 Prompt Bar Routes to Chat

**File**: `choiros/src/components/apps/Chat.tsx`

- All prompts go through Chat and create `chat.message.create` + `tool.call` events
- Tool results render as timeline cards with provenance

### OBSERVE
- Chat shows tool-call cards with tool name, args, and result
- Message list can be toggled but is not the default
- Prompt bar always emits tool-call ledger events

---

## Phase 3: App Spawning + View Sync

### PREDICTION
Writer, Context Heatmap, Runmap, and Audit can be opened from Chat and stay in sync by session.

### EXPERIMENT

#### 3.1 App Spawn Events

**File**: `choiros/src/stores/useWindowStore.ts`

- Emit `app.spawn` with `session_id`, `app_id`, and `view_context`
- Emit `app.focus` when the window is activated

#### 3.2 View Sync Events

**File**: `choiros/src/lib/nats.ts`

- Each app subscribes to `tool.call` and `tool.result` scoped by session
- Emit `app.view.sync` when an app changes filters or selected context

### OBSERVE
- Chat spawns Writer/Heatmap/Runmap/Audit windows with the same `session_id`
- Each app updates when new tool calls are logged
- View context changes are visible to other apps

---

## Phase 4: Writer as Projection of Tool Calls

### PREDICTION
Writer renders the document as a projection of tool calls and can show provenance for each edit.

### EXPERIMENT

#### 4.1 Document Events Remain First-Class

**Files**:
- `api/routers/documents.py`
- `supervisor/db.py`
- `supervisor/event_publisher.py`

Keep document events (`document.create`, `document.edit`, `document.snapshot`, `document.restore`) but:
- Each `document.edit` references a `tool_call_id`
- Writer pulls edits from the tool-call ledger for provenance

#### 4.2 Writer UI Shows Provenance

**File**: `choiros/src/components/apps/Writer.tsx`

- Display recent edits with the associated tool call
- Provide an Audit toggle to see why a change happened

### OBSERVE
- Writer renders document state and a linked edit history
- Each edit links to a tool-call entry in the ledger
- Audit view can explain the origin of edits

---

## Phase 5: Real-Time Collaboration (Optional)

### PREDICTION
CRDT operations can be recorded in the tool-call ledger without losing real-time collaboration.

### EXPERIMENT

- Integrate Yjs for real-time collaboration
- Emit CRDT ops as `document.edit` events with a `tool_call_id`
- Persist CRDT operations in the ledger

### OBSERVE
- Concurrent edits resolve correctly
- Tool-call ledger reflects CRDT operations
- Writer stays consistent across clients

---

## Testing & Validation

```bash
# Ledger API
cd api
pytest path/to/test_ledger.py -v

# Documents API
pytest tests/test_documents.py -v

# Manual UI test
# 1. Open Chat and submit a prompt
# 2. Verify tool-call timeline updates
# 3. Spawn Writer/Heatmap/Runmap/Audit
# 4. Verify all views stay in sync
```

---

## Success Criteria

- [x] Chat is the default app with prompt bar and tool-call timeline
- [x] Tool calls are recorded and queryable by session
- [x] Writer, Heatmap, Runmap, and Audit subscribe to the same ledger
- [x] Document edits link back to tool-call provenance
- [ ] Real-time collaboration via CRDTs (optional)

---

**End of Runbook**
