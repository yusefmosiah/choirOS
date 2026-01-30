# Collaborative Document Editing Implementation Runbook

**Date**: 2026-01-29
**Based on**: `docs/research/COLLABORATIVE_DOCUMENT_EDITING_RESEARCH.md`
**Context**: Implement prompt-bar writer app with snapshot version control and AI co-editing

**Architecture Notes**:
- **No Burr**: Using existing Machine + AgentHarness + RunOrchestrator
- **Event Sourcing**: NATS JetStream (immutable source of truth)
- **Projection**: libsql (materialized state)
- **Real-time**: NATS WebSocket to browser
- **CRDT**: Deferred to Phase 3 (start with event-based edits)

---

## Phase 1: Document Events (Event Sourcing)

### PREDICTION
Documents can be created, edited, and restored from NATS events with version tracking.

### EXPERIMENT

#### 1.1 Add Document Event Types to Event Contract

**File**: `supervisor/event_contract.py`

```python
# Add to CHOIR_EVENT_TYPES_V0
"document.create",
"document.edit",
"document.snapshot",
"document.restore",
"ai.suggestion",
"ai.suggestion.accept",
"ai.suggestion.reject",
```

**File**: `choiros/src/lib/event_contract.ts`

```typescript
export const CHOIR_EVENT_TYPES_V0 = [
    // ... existing events
    'document.create',
    'document.edit',
    'document.snapshot',
    'document.restore',
    'ai.suggestion',
    'ai.suggestion.accept',
    'ai.suggestion.reject',
] as const;
```

#### 1.2 Create Document Router in Backend

**File**: `api/routers/documents.py` (new file)

```python
"""Document router - collaborative editing endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class DocumentCreateRequest(BaseModel):
    title: str
    content: str
    metadata: dict = {}

class DocumentEditRequest(BaseModel):
    document_id: str
    operation: str  # "insert", "delete", "replace"
    position: Optional[int] = None
    start: Optional[int] = None
    end: Optional[int] = None
    new_content: Optional[str] = None
    reason: Optional[str] = None

class DocumentSnapshotRequest(BaseModel):
    document_id: str
    label: Optional[str] = None
    metadata: dict = {}

class DocumentRestoreRequest(BaseModel):
    document_id: str
    snapshot_id: str
    reason: Optional[str] = None

router = APIRouter()

@router.post("/documents")
async def create_document(request: DocumentCreateRequest):
    """Create a new document."""
    from supervisor.event_publisher import get_publisher
    from shared.auth import get_auth_store
    import json
    
    # Get user ID from session
    session = get_auth_store().verify_session()
    user_id = session.user_id if session else "local"
    publisher = get_publisher(user_id)
    
    document_id = str(uuid.uuid4())
    
    await publisher.publish(
        "document.create",
        {
            "document_id": document_id,
            "title": request.title,
            "content": request.content,
            "metadata": request.metadata,
        },
        source="user",
    )
    
    return {"document_id": document_id, "status": "created"}

@router.post("/documents/edit")
async def edit_document(request: DocumentEditRequest):
    """Edit a document with AI or human."""
    from supervisor.event_publisher import get_publisher
    from shared.auth import get_auth_store
    
    session = get_auth_store().verify_session()
    user_id = session.user_id if session else "local"
    publisher = get_publisher(user_id)
    
    await publisher.publish(
        "document.edit",
        {
            "document_id": request.document_id,
            "operation": request.operation,
            "position": request.position,
            "start": request.start,
            "end": request.end,
            "new_content": request.new_content,
            "reason": request.reason,
        },
        source="user",
    )
    
    return {"document_id": request.document_id, "status": "edited"}

@router.post("/documents/snapshot")
async def create_snapshot(request: DocumentSnapshotRequest):
    """Create a version snapshot."""
    from supervisor.event_publisher import get_publisher
    from supervisor.db import get_store
    from shared.auth import get_auth_store
    
    session = get_auth_store().verify_session()
    user_id = session.user_id if session else "local"
    publisher = get_publisher(user_id)
    store = get_store(user_id)
    
    # Get current document state
    doc = store.get_document(request.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    snapshot_id = str(uuid.uuid4())
    
    await publisher.publish(
        "document.snapshot",
        {
            "snapshot_id": snapshot_id,
            "document_id": request.document_id,
            "content": doc["content"],
            "label": request.label or f"Snapshot {len(store.list_snapshots(request.document_id)) + 1}",
            "metadata": request.metadata,
        },
        source="user",
    )
    
    return {"snapshot_id": snapshot_id, "document_id": request.document_id}

@router.post("/documents/restore")
async def restore_snapshot(request: DocumentRestoreRequest):
    """Restore document to a snapshot."""
    from supervisor.event_publisher import get_publisher
    from supervisor.db import get_store
    from shared.auth import get_auth_store
    
    session = get_auth_store().verify_session()
    user_id = session.user_id if session else "local"
    publisher = get_publisher(user_id)
    store = get_store(user_id)
    
    snapshot = store.get_snapshot(request.snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    await publisher.publish(
        "document.restore",
        {
            "snapshot_id": request.snapshot_id,
            "document_id": request.document_id,
            "content": snapshot["content"],
            "reason": request.reason,
        },
        source="user",
    )
    
    return {"document_id": request.document_id, "status": "restored"}

@router.get("/documents/{document_id}")
async def get_document(document_id: str):
    """Get document current state."""
    from supervisor.db import get_store
    from shared.auth import get_auth_store
    
    session = get_auth_store().verify_session()
    user_id = session.user_id if session else "local"
    store = get_store(user_id)
    
    doc = store.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return doc

@router.get("/documents/{document_id}/snapshots")
async def list_snapshots(document_id: str):
    """List all snapshots for a document."""
    from supervisor.db import get_store
    from shared.auth import get_auth_store
    
    session = get_auth_store().verify_session()
    user_id = session.user_id if session else "local"
    store = get_store(user_id)
    
    snapshots = store.list_snapshots(document_id)
    return {"snapshots": snapshots}
```

#### 1.3 Add Document Projection Tables

**File**: `supervisor/db.py`

Add to `_init_schema()` method:

```python
# Add after existing tables
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    metadata JSON,
    current_snapshot_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at);

CREATE TABLE IF NOT EXISTS document_snapshots (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id),
    content TEXT NOT NULL,
    label TEXT,
    metadata JSON,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    parent_snapshot_id TEXT REFERENCES document_snapshots(id),
    is_current INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_snapshots_document ON document_snapshots(document_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_created ON document_snapshots(created_at);

CREATE TABLE IF NOT EXISTS document_edits (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id),
    snapshot_id TEXT REFERENCES document_snapshots(id),
    operation TEXT NOT NULL,
    position INTEGER,
    start_pos INTEGER,
    end_pos INTEGER,
    new_content TEXT,
    reason TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_edits_document ON document_edits(document_id);
CREATE INDEX IF NOT EXISTS idx_edits_snapshot ON document_edits(snapshot_id);
```

Add methods to `ProjectionStore` class:

```python
def get_document(self, document_id: str) -> Optional[dict]:
    """Get document current state."""
    cursor = self.conn.execute(
        "SELECT * FROM documents WHERE id = ?",
        (document_id,)
    )
    row = cursor.fetchone()
    if not row:
        return None
    doc = dict(row)
    if doc.get("metadata"):
        try:
            doc["metadata"] = json.loads(doc["metadata"])
        except:
            doc["metadata"] = {}
    return doc

def list_documents(self, limit: int = 50) -> list[dict]:
    """List all documents."""
    cursor = self.conn.execute(
        "SELECT * FROM documents ORDER BY updated_at DESC LIMIT ?",
        (limit,)
    )
    docs = []
    for row in cursor.fetchall():
        doc = dict(row)
        if doc.get("metadata"):
            try:
                doc["metadata"] = json.loads(doc["metadata"])
            except:
                doc["metadata"] = {}
        docs.append(doc)
    return docs

def get_snapshot(self, snapshot_id: str) -> Optional[dict]:
    """Get a snapshot."""
    cursor = self.conn.execute(
        "SELECT * FROM document_snapshots WHERE id = ?",
        (snapshot_id,)
    )
    row = cursor.fetchone()
    if not row:
        return None
    snapshot = dict(row)
    if snapshot.get("metadata"):
        try:
            snapshot["metadata"] = json.loads(snapshot["metadata"])
        except:
            snapshot["metadata"] = {}
    return snapshot

def list_snapshots(self, document_id: str) -> list[dict]:
    """List all snapshots for a document."""
    cursor = self.conn.execute(
        "SELECT * FROM document_snapshots WHERE document_id = ? ORDER BY created_at DESC",
        (document_id,)
    )
    snapshots = []
    for row in cursor.fetchall():
        snapshot = dict(row)
        if snapshot.get("metadata"):
            try:
                snapshot["metadata"] = json.loads(snapshot["metadata"])
            except:
                snapshot["metadata"] = {}
        snapshots.append(snapshot)
    return snapshots
```

Add to `_materialize_projection()` method:

```python
elif event_type == "document.create":
    document_id = payload.get("document_id")
    if document_id:
        self.conn.execute(
            """INSERT INTO documents (id, title, content, metadata)
               VALUES (?, ?, ?, ?)""",
            (document_id, payload.get("title"), payload.get("content"), json.dumps(payload.get("metadata", {}))),
        )
elif event_type == "document.edit":
    document_id = payload.get("document_id")
    if document_id:
        operation = payload.get("operation")
        content = payload.get("content")
        doc = self.get_document(document_id)
        if doc:
            new_content = doc["content"]
            if operation == "insert" and payload.get("position") is not None:
                pos = payload["position"]
                new_content = new_content[:pos] + payload.get("new_content", "") + new_content[pos:]
            elif operation == "delete" and payload.get("start") is not None and payload.get("end") is not None:
                start = payload["start"]
                end = payload["end"]
                new_content = new_content[:start] + new_content[end:]
            elif operation == "replace" and payload.get("start") is not None and payload.get("end") is not None:
                start = payload["start"]
                end = payload["end"]
                new_content = new_content[:start] + payload.get("new_content", "") + new_content[end:]
            
            # Update document
            self.conn.execute(
                """UPDATE documents SET content = ?, updated_at = ? WHERE id = ?""",
                (new_content, timestamp, document_id),
            )
            
            # Record edit
            edit_id = str(uuid.uuid4())
            self.conn.execute(
                """INSERT INTO document_edits (id, document_id, snapshot_id, operation, position, start_pos, end_pos, new_content, reason, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (edit_id, document_id, doc.get("current_snapshot_id"), operation, payload.get("position"), payload.get("start"), payload.get("end"), payload.get("new_content"), payload.get("reason"), timestamp),
            )
elif event_type == "document.snapshot":
    snapshot_id = payload.get("snapshot_id")
    document_id = payload.get("document_id")
    if snapshot_id and document_id:
        self.conn.execute(
            """INSERT INTO document_snapshots (id, document_id, content, label, metadata, parent_snapshot_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (snapshot_id, document_id, payload.get("content"), payload.get("label"), json.dumps(payload.get("metadata", {})), payload.get("parent_snapshot_id")),
        )
        # Update current snapshot reference
        self.conn.execute(
            "UPDATE documents SET current_snapshot_id = ?, updated_at = ? WHERE id = ?",
            (snapshot_id, timestamp, document_id),
        )
elif event_type == "document.restore":
    snapshot_id = payload.get("snapshot_id")
    document_id = payload.get("document_id")
    if snapshot_id and document_id:
        snapshot = self.get_snapshot(snapshot_id)
        if snapshot:
            self.conn.execute(
                """UPDATE documents SET content = ?, current_snapshot_id = ?, updated_at = ? WHERE id = ?""",
                (snapshot["content"], snapshot_id, timestamp, document_id),
            )
```

#### 1.4 Mount Document Router

**File**: `api/main.py`

```python
from api.routers import documents

app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
```

#### 1.5 Test Document Events

**File**: `api/tests/test_documents.py` (new file)

```python
"""Test document event sourcing."""

import pytest
from httpx import AsyncClient
from api.main import app

@pytest.mark.asyncio
async def test_create_document():
    """PREDICTION: Creating a document emits document.create event."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/documents",
            json={"title": "Test Doc", "content": "Hello World", "metadata": {}}
        )
        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert data["status"] == "created"

@pytest.mark.asyncio
async def test_edit_document():
    """PREDICTION: Editing a document emits document.edit event."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create
        create_resp = await client.post(
            "/api/documents",
            json={"title": "Test Doc", "content": "Hello World"}
        )
        doc_id = create_resp.json()["document_id"]
        
        # Edit
        edit_resp = await client.post(
            "/api/documents/edit",
            json={
                "document_id": doc_id,
                "operation": "insert",
                "position": 5,
                "new_content": " Beautiful"
            }
        )
        assert edit_resp.status_code == 200
        
        # Verify
        get_resp = await client.get(f"/api/documents/{doc_id}")
        doc = get_resp.json()
        assert "Hello Beautiful World" == doc["content"]

@pytest.mark.asyncio
async def test_snapshot_and_restore():
    """PREDICTION: Snapshots can be created and restored."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        create_resp = await client.post(
            "/api/documents",
            json={"title": "Test Doc", "content": "Version 1"}
        )
        doc_id = create_resp.json()["document_id"]
        
        # Create snapshot
        snap_resp = await client.post(
            "/api/documents/snapshot",
            json={"document_id": doc_id, "label": "First version"}
        )
        snapshot_id = snap_resp.json()["snapshot_id"]
        
        # Edit
        await client.post(
            "/api/documents/edit",
            json={
                "document_id": doc_id,
                "operation": "replace",
                "start": 0,
                "end": 9,
                "new_content": "Version 2"
            }
        )
        
        # Restore
        await client.post(
            "/api/documents/restore",
            json={
                "document_id": doc_id,
                "snapshot_id": snapshot_id,
                "reason": "Testing restore"
            }
        )
        
        # Verify
        get_resp = await client.get(f"/api/documents/{doc_id}")
        doc = get_resp.json()
        assert doc["content"] == "Version 1"
```

### OBSERVE
- NATS JetStream has `document.create`, `document.edit`, `document.snapshot`, `document.restore` events
- libsql `documents` table shows current document states
- libsql `document_snapshots` table tracks version history
- libsql `document_edits` table records all edit operations
- Document content reconstructable from event sequence

---

## Phase 2: AI Editing Tools

### PREDICTION
AI can edit documents through prompt bar with accept/reject workflow.

### EXPERIMENT

#### 2.1 Add Document Edit Tool to Agent

**File**: `supervisor/agent/tools.py`

Add to `TOOL_DEFINITIONS`:

```python
{
    "name": "edit_document",
    "description": "Edit a document (insert, delete, or replace text). Use this when user asks to revise, expand, or rewrite content.",
    "input_schema": {
        "type": "object",
        "properties": {
            "document_id": {
                "type": "string",
                "description": "Document ID to edit",
            },
            "operation": {
                "type": "string",
                "enum": ["insert", "delete", "replace"],
                "description": "Type of edit operation",
            },
            "position": {
                "type": "number",
                "description": "Position for insert operation (character index)",
            },
            "start": {
                "type": "number",
                "description": "Start position for delete/replace",
            },
            "end": {
                "type": "number",
                "description": "End position for delete/replace",
            },
            "new_content": {
                "type": "string",
                "description": "New content to insert or replace with",
            },
            "reason": {
                "type": "string",
                "description": "Why this edit was made",
            },
        },
        "required": ["document_id", "operation"],
    },
}
```

Add to `AgentTools.execute_tool()`:

```python
elif tool_name == "edit_document":
    from supervisor.event_publisher import get_publisher
    
    document_id = args.get("document_id")
    operation = args.get("operation")
    
    await publisher.publish(
        "document.edit",
        {
            "document_id": document_id,
            "operation": operation,
            "position": args.get("position"),
            "start": args.get("start"),
            "end": args.get("end"),
            "new_content": args.get("new_content"),
            "reason": args.get("reason"),
        },
        source="agent",
    )
    return {"status": "edited", "document_id": document_id}
```

#### 2.2 Add Document Query Tool

```python
{
    "name": "get_document",
    "description": "Get the current content of a document",
    "input_schema": {
        "type": "object",
        "properties": {
            "document_id": {
                "type": "string",
                "description": "Document ID",
            },
        },
        "required": ["document_id"],
    },
}

elif tool_name == "get_document":
    from supervisor.db import get_store
    store = get_store()
    doc = store.get_document(args.get("document_id"))
    return doc if doc else {"error": "Document not found"}
```

### OBSERVE
- Agent can call `edit_document` tool
- AI edits emit `document.edit` events with source="agent"
- AI edits are recorded in `document_edits` table
- Document content updates after AI edit

---

## Phase 3: Updated Writer UI (Prompt Bar Pattern)

### PREDICTION
Writer app shows document editor + prompt bar at bottom, not chat sidebar.

### EXPERIMENT

**File**: `choiros/src/components/apps/Writer.tsx`

```typescript
import { useState, useEffect, useRef } from 'react';
import { useAgent } from '../../hooks/useAgent';
import { publishEvent, subscribeEvents } from '../../lib/nats';
import './Writer.css';

interface Document {
    id: string;
    title: string;
    content: string;
    created_at: string;
    updated_at: string;
}

interface Snapshot {
    id: string;
    document_id: string;
    content: string;
    label: string;
    created_at: string;
}

export function Writer() {
    const [document, setDocument] = useState<Document | null>(null);
    const [content, setContent] = useState('');
    const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
    const [selectedSnapshot, setSelectedSnapshot] = useState<Snapshot | null>(null);
    const [showSnapshotPanel, setShowSnapshotPanel] = useState(false);
    const [prompt, setPrompt] = useState('');
    const [isProcessing, setIsProcessing] = useState(false);
    
    const { sendPrompt, isConnected } = useAgent();
    
    // Load document (use documentId from window props or create new)
    useEffect(() => {
        // For now, create a new document
        createNewDocument();
    }, []);
    
    // Subscribe to document edits from NATS
    useEffect(() => {
        if (!document) return;
        
        const unsubscribe = subscribeEvents(
            `choiros.local.>document.edit`,
            (event) => {
                if (event.payload.document_id === document.id) {
                    // Reload document
                    loadDocument(document.id);
                }
            }
        );
        
        return unsubscribe;
    }, [document]);
    
    const createNewDocument = async () => {
        const response = await fetch('http://localhost:8000/api/documents', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: 'Untitled Document',
                content: '',
            }),
        });
        const data = await response.json();
        setDocument(data);
        setContent('');
        loadSnapshots(data.document_id);
    };
    
    const loadDocument = async (docId: string) => {
        const response = await fetch(`http://localhost:8000/api/documents/${docId}`);
        const data = await response.json();
        setDocument(data);
        setContent(data.content);
    };
    
    const loadSnapshots = async (docId: string) => {
        const response = await fetch(`http://localhost:8000/api/documents/${docId}/snapshots`);
        const data = await response.json();
        setSnapshots(data.snapshots);
    };
    
    const handleContentChange = (newContent: string) => {
        setContent(newContent);
        // Debounce edit
        clearTimeout(editTimeoutRef.current);
        editTimeoutRef.current = setTimeout(() => {
            publishEvent('document.edit', {
                document_id: document.id,
                operation: 'replace',
                start: 0,
                end: content.length,
                new_content: newContent,
                reason: 'User manual edit',
            }, 'user');
        }, 1000);
    };
    
    const editTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    
    const createSnapshot = async () => {
        const label = prompt('Snapshot label:');
        if (!label) return;
        
        const response = await fetch('http://localhost:8000/api/documents/snapshot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                document_id: document.id,
                label,
            }),
        });
        const data = await response.json();
        loadSnapshots(document.id);
    };
    
    const restoreSnapshot = async (snapshotId: string) => {
        const response = await fetch('http://localhost:8000/api/documents/restore', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                document_id: document.id,
                snapshot_id: snapshotId,
                reason: 'User manual restore',
            }),
        });
        await response.json();
        loadDocument(document.id);
        setSelectedSnapshot(null);
    };
    
    const handlePromptSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!prompt.trim() || isProcessing) return;
        
        setIsProcessing(true);
        
        // Send to agent with context
        const fullPrompt = `Document: ${document.title}\n\n${content}\n\nUser request: ${prompt}`;
        sendPrompt(fullPrompt);
        
        setPrompt('');
    };
    
    if (!document) {
        return <div className="writer-loading">Loading...</div>;
    }
    
    return (
        <div className="writer">
            {/* Header */}
            <div className="writer-header">
                <input
                    className="writer-title"
                    value={document.title}
                    onChange={(e) => {/* Update title */}}
                />
                <button onClick={createSnapshot}>Save Version</button>
                <button onClick={() => setShowSnapshotPanel(!showSnapshotPanel)}>
                    History {snapshots.length}
                </button>
            </div>
            
            {/* Editor */}
            <textarea
                className="writer-editor"
                value={content}
                onChange={(e) => handleContentChange(e.target.value)}
                placeholder="Start writing..."
            />
            
            {/* Snapshot Panel (slide-out) */}
            {showSnapshotPanel && (
                <div className="writer-snapshots">
                    <h3>Version History</h3>
                    {snapshots.map((snap) => (
                        <div key={snap.id} className="snapshot-item">
                            <div className="snapshot-info">
                                <strong>{snap.label}</strong>
                                <small>{new Date(snap.created_at).toLocaleString()}</small>
                            </div>
                            <button onClick={() => setSelectedSnapshot(snap)}>View</button>
                            <button onClick={() => restoreSnapshot(snap.id)}>Restore</button>
                        </div>
                    ))}
                </div>
            )}
            
            {/* Snapshot Preview */}
            {selectedSnapshot && (
                <div className="writer-preview">
                    <h3>Snapshot: {selectedSnapshot.label}</h3>
                    <pre>{selectedSnapshot.content}</pre>
                    <button onClick={() => setSelectedSnapshot(null)}>Close</button>
                </div>
            )}
            
            {/* Prompt Bar */}
            <form className="writer-prompt-bar" onSubmit={handlePromptSubmit}>
                <input
                    type="text"
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Revise conclusion, expand section 2, simplify this paragraph..."
                    disabled={isProcessing}
                />
                <button type="submit" disabled={isProcessing || !prompt.trim()}>
                    {isProcessing ? 'Thinking...' : 'Send'}
                </button>
            </form>
            
            {/* Quick Actions */}
            <div className="writer-quick-actions">
                <button onClick={() => sendPrompt('Make this more concise')}>Simplify</button>
                <button onClick={() => sendPrompt('Expand with more detail')}>Expand</button>
                <button onClick={() => sendPrompt('Improve the writing style')}>Polish</button>
            </div>
        </div>
    );
}
```

**File**: `choiros/src/components/apps/Writer.css`

```css
.writer {
    display: flex;
    flex-direction: column;
    height: 100vh;
    background: #1e1e1e;
    color: #fff;
}

.writer-header {
    display: flex;
    gap: 10px;
    padding: 10px;
    background: #252526;
    border-bottom: 1px solid #333;
}

.writer-title {
    flex: 1;
    background: #3c3c3c;
    border: 1px solid #555;
    color: #fff;
    padding: 5px 10px;
    font-size: 14px;
}

.writer-editor {
    flex: 1;
    background: #1e1e1e;
    color: #d4d4d4;
    border: none;
    padding: 20px;
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    resize: none;
    outline: none;
}

.writer-snapshots {
    position: fixed;
    right: 0;
    top: 0;
    bottom: 60px;
    width: 300px;
    background: #252526;
    border-left: 1px solid #333;
    padding: 20px;
    overflow-y: auto;
    transform: translateX(100%);
    transition: transform 0.3s ease;
}

.writer-snapshots.show {
    transform: translateX(0);
}

.snapshot-item {
    display: flex;
    flex-direction: column;
    gap: 5px;
    padding: 10px;
    background: #2d2d30;
    border-radius: 4px;
    margin-bottom: 10px;
}

.snapshot-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.writer-preview {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 80%;
    max-height: 80%;
    background: #252526;
    border: 1px solid #454545;
    border-radius: 8px;
    padding: 20px;
    overflow-y: auto;
}

.writer-prompt-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    gap: 10px;
    padding: 10px 20px;
    background: #2d2d30;
    border-top: 1px solid #454545;
}

.writer-prompt-bar input {
    flex: 1;
    background: #3c3c3c;
    border: 1px solid #555;
    color: #fff;
    padding: 10px;
    border-radius: 4px;
    font-size: 14px;
}

.writer-prompt-bar button {
    background: #0078d4;
    color: #fff;
    border: none;
    padding: 10px 20px;
    border-radius: 4px;
    cursor: pointer;
}

.writer-prompt-bar button:disabled {
    background: #555;
    cursor: not-allowed;
}

.writer-quick-actions {
    display: flex;
    gap: 10px;
    padding: 10px 20px;
    background: #2d2d30;
    border-top: 1px solid #333;
}

.writer-quick-actions button {
    background: transparent;
    color: #0078d4;
    border: 1px solid #0078d4;
    padding: 5px 10px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
}

.writer-quick-actions button:hover {
    background: #0078d4;
    color: #fff;
}
```

### OBSERVE
- Writer shows full-screen document editor
- Prompt bar at bottom (not chat sidebar)
- "Save Version" button creates snapshots
- "History" panel shows version history
- "Simplify", "Expand", "Polish" quick actions
- AI edits update document content via NATS

---

## Phase 4: Turn-Based AI Edits with Snapshots

### PREDICTION
Each AI operation creates a snapshot before editing for easy rollback.

### EXPERIMENT

#### 4.1 Auto-Snapshot Before AI Edits

**File**: `supervisor/agent/tools.py` (update `edit_document` tool)

```python
elif tool_name == "edit_document":
    from supervisor.event_publisher import get_publisher
    from supervisor.db import get_store
    
    document_id = args.get("document_id")
    operation = args.get("operation")
    store = get_store()
    
    # Get current document
    doc = store.get_document(document_id)
    if not doc:
        return {"error": "Document not found"}
    
    # Create snapshot before AI edit
    snapshot_id = str(uuid.uuid4())
    await publisher.publish(
        "document.snapshot",
        {
            "snapshot_id": snapshot_id,
            "document_id": document_id,
            "content": doc["content"],
            "label": f"Before AI edit: {operation}",
            "metadata": {"ai_edit": True, "operation": operation},
        },
        source="agent",
    )
    
    # Perform edit
    await publisher.publish(
        "document.edit",
        {
            "document_id": document_id,
            "operation": operation,
            "position": args.get("position"),
            "start": args.get("start"),
            "end": args.get("end"),
            "new_content": args.get("new_content"),
            "reason": args.get("reason"),
        },
        source="agent",
    )
    
    return {
        "status": "edited",
        "document_id": document_id,
        "snapshot_id": snapshot_id,
    }
```

#### 4.2 Turn Number in Snapshots

**File**: `supervisor/db.py` (add turn tracking)

```python
# In _init_schema, update document_snapshots table
# Add: turn_number INTEGER
```

Update snapshot creation:

```python
elif event_type == "document.snapshot":
    snapshot_id = payload.get("snapshot_id")
    document_id = payload.get("document_id")
    if snapshot_id and document_id:
        # Get current turn number
        cursor = self.conn.execute(
            "SELECT MAX(turn_number) FROM document_snapshots WHERE document_id = ?",
            (document_id,)
        )
        max_turn = cursor.fetchone()[0] or 0
        turn_number = max_turn + 1
        
        self.conn.execute(
            """INSERT INTO document_snapshots (id, document_id, content, label, metadata, parent_snapshot_id, turn_number)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (snapshot_id, document_id, payload.get("content"), payload.get("label"), json.dumps(payload.get("metadata", {})), payload.get("parent_snapshot_id"), turn_number),
        )
```

### OBSERVE
- Each AI edit creates an automatic snapshot
- Snapshots have turn numbers for version tracking
- Users can easily revert any AI edit
- Turn history shows progression of document

---

## Phase 5: AI Suggestions (Accept/Reject)

### PREDICTION
AI suggestions appear as diff previews that user can accept or reject.

### EXPERIMENT

#### 5.1 Suggestion Events

Add to event contract (Phase 1 already did this).

#### 5.2 Create Suggestion Projection Table

**File**: `supervisor/db.py`

```python
CREATE TABLE IF NOT EXISTS ai_suggestions (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id),
    snapshot_id TEXT REFERENCES document_snapshots(id),
    diff TEXT NOT NULL,  -- JSON diff
    operation TEXT,
    start_pos INTEGER,
    end_pos INTEGER,
    new_content TEXT,
    status TEXT DEFAULT 'pending',  -- 'pending', 'accepted', 'rejected'
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_suggestions_document ON ai_suggestions(document_id);
CREATE INDEX IF NOT EXISTS idx_suggestions_status ON ai_suggestions(status);
```

#### 5.3 Suggestion Tool

**File**: `supervisor/agent/tools.py`

```python
{
    "name": "suggest_edit",
    "description": "Suggest an edit to the document (user must accept/reject)",
    "input_schema": {
        "type": "object",
        "properties": {
            "document_id": {"type": "string"},
            "operation": {"type": "string", "enum": ["insert", "delete", "replace"]},
            "start": {"type": "number"},
            "end": {"type": "number"},
            "new_content": {"type": "string"},
            "reason": {"type": "string"},
        },
        "required": ["document_id", "operation"],
    },
}

elif tool_name == "suggest_edit":
    from supervisor.event_publisher import get_publisher
    import json
    
    suggestion_id = str(uuid.uuid4())
    
    await publisher.publish(
        "ai.suggestion",
        {
            "suggestion_id": suggestion_id,
            "document_id": args.get("document_id"),
            "operation": args.get("operation"),
            "start": args.get("start"),
            "end": args.get("end"),
            "new_content": args.get("new_content"),
            "reason": args.get("reason"),
            "diff": json.dumps({
                "operation": args.get("operation"),
                "start": args.get("start"),
                "end": args.get("end"),
                "new_content": args.get("new_content"),
            }),
        },
        source="agent",
    )
    
    return {"suggestion_id": suggestion_id, "status": "pending"}
```

#### 5.4 Accept/Reject Suggestion API

**File**: `api/routers/documents.py`

```python
class SuggestionActionRequest(BaseModel):
    suggestion_id: str
    action: str  # "accept" or "reject"

@router.post("/documents/suggestions/action")
async def handle_suggestion(request: SuggestionActionRequest):
    """Accept or reject an AI suggestion."""
    from supervisor.event_publisher import get_publisher
    from supervisor.db import get_store
    from shared.auth import get_auth_store
    
    session = get_auth_store().verify_session()
    user_id = session.user_id if session else "local"
    publisher = get_publisher(user_id)
    store = get_store(user_id)
    
    suggestion = store.get_suggestion(request.suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    if request.action == "accept":
        # Apply the edit
        await publisher.publish(
            "document.edit",
            {
                "document_id": suggestion["document_id"],
                "operation": suggestion["operation"],
                "start": suggestion["start_pos"],
                "end": suggestion["end_pos"],
                "new_content": suggestion["new_content"],
                "reason": f"Accepted suggestion: {suggestion['reason']}",
            },
            source="user",
        )
    
    await publisher.publish(
        f"ai.suggestion.{request.action}",
        {
            "suggestion_id": request.suggestion_id,
            "action": request.action,
        },
        source="user",
    )
    
    return {"suggestion_id": request.suggestion_id, "action": request.action}
```

#### 5.5 UI for Suggestions

**File**: `choiros/src/components/apps/Writer.tsx`

Add suggestion state and display:

```typescript
const [suggestions, setSuggestions] = useState<any[]>([]);

useEffect(() => {
    if (!document) return;
    
    const unsubscribe = subscribeEvents(
        `choiros.local.>ai.suggestion`,
        (event) => {
            if (event.payload.document_id === document.id) {
                setSuggestions(prev => [...prev, event.payload]);
            }
        }
    );
    
    return unsubscribe;
}, [document]);

const acceptSuggestion = async (suggestion: any) => {
    await fetch('http://localhost:8000/api/documents/suggestions/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            suggestion_id: suggestion.suggestion_id,
            action: 'accept',
        }),
    });
    setSuggestions(prev => prev.filter(s => s.suggestion_id !== suggestion.suggestion_id));
};

// Render suggestions above prompt bar
{suggestions.map((suggestion) => (
    <div key={suggestion.suggestion_id} className="writer-suggestion">
        <div className="suggestion-diff">
            {/* Show diff visualization */}
            <span className="diff-removed">{content.slice(suggestion.start, suggestion.end)}</span>
            <span className="diff-added">{suggestion.new_content}</span>
        </div>
        <div className="suggestion-reason">{suggestion.reason}</div>
        <div className="suggestion-actions">
            <button onClick={() => acceptSuggestion(suggestion)}>Accept</button>
            <button onClick={() => setSuggestions(prev => prev.filter(s => s.suggestion_id !== suggestion.suggestion_id))}>Reject</button>
        </div>
    </div>
))}
```

### OBSERVE
- AI suggestions appear as inline diffs
- User can "Accept" (applies edit) or "Reject" (dismisses suggestion)
- Accepted suggestions create `document.edit` event
- Suggestions table tracks status (pending/accepted/rejected)

---

## Phase 6: Diff Visualization

### PREDICTION
Users can see diff between any two versions of the document.

### EXPERIMENT

#### 6.1 Diff API Endpoint

**File**: `api/routers/documents.py`

```python
class DiffRequest(BaseModel):
    document_id: str
    from_snapshot_id: Optional[str] = None
    to_snapshot_id: Optional[str] = None

@router.post("/documents/diff")
async def diff_versions(request: DiffRequest):
    """Generate diff between two snapshots."""
    from supervisor.db import get_store
    from shared.auth import get_auth_store
    
    session = get_auth_store().verify_session()
    user_id = session.user_id if session else "local"
    store = get_store(user_id)
    
    if request.from_snapshot_id:
        from_snap = store.get_snapshot(request.from_snapshot_id)
    else:
        from_snap = store.get_document(request.document_id)
    
    if request.to_snapshot_id:
        to_snap = store.get_snapshot(request.to_snapshot_id)
    else:
        to_snap = store.get_document(request.document_id)
    
    if not from_snap or not to_snap:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    # Simple line-by-line diff
    from_lines = from_snap["content"].split("\n")
    to_lines = to_snap["content"].split("\n")
    
    import difflib
    diff = list(difflib.unified_diff(from_lines, to_lines, lineterm=""))
    
    return {
        "from_snapshot_id": request.from_snapshot_id,
        "to_snapshot_id": request.to_snapshot_id,
        "diff": diff,
    }
```

#### 6.2 UI for Diff View

**File**: `choiros/src/components/apps/Writer.tsx`

Add diff modal when comparing snapshots:

```typescript
const [diffView, setDiffView] = useState<{from: string, to: string} | null>(null);
const [diff, setDiff] = useState<string[] | null>(null);

const compareSnapshots = async (fromId: string, toId: string) => {
    const response = await fetch('http://localhost:8000/api/documents/diff', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            document_id: document.id,
            from_snapshot_id: fromId,
            to_snapshot_id: toId,
        }),
    });
    const data = await response.json();
    setDiffView({ from: fromId, to: toId });
    setDiff(data.diff);
};

// Add "Compare" button to snapshot items
<button onClick={() => compareSnapshots(snapshots[0].id, snapshot.id)}>
    Compare
</button>

// Diff modal
{diffView && diff && (
    <div className="writer-diff-modal">
        <h3>Version Comparison</h3>
        <pre className="diff-output">{diff.join('\n')}</pre>
        <button onClick={() => setDiffView(null)}>Close</button>
    </div>
)}
```

### OBSERVE
- Users can compare any two snapshots
- Diff shows added/removed lines
- Visual feedback for document changes

---

## Testing & Validation

### Test All Phases

```bash
# Phase 1: Document Events
cd api
pytest tests/test_documents.py -v

# Phase 2: AI Editing
# Manual test through Writer UI
# 1. Create document
# 2. Type "Revise the conclusion to be more compelling"
# 3. Verify AI edits document

# Phase 3: Prompt Bar
# Manual test
# 1. Verify prompt bar at bottom
# 2. Test quick actions (Simplify, Expand, Polish)
# 3. Verify no chat sidebar

# Phase 4: Turn-Based
# Manual test
# 1. Create snapshot "Turn 1"
# 2. Ask AI to edit
# 3. Verify auto-snapshot created
# 4. Restore to "Turn 1"

# Phase 5: Suggestions
# Manual test
# 1. Ask AI to suggest edit
# 2. Verify suggestion appears as diff
# 3. Accept suggestion
# 4. Verify edit applied

# Phase 6: Diff
# Manual test
# 1. Create 2 snapshots
# 2. Compare them
# 3. Verify diff visualization
```

---

## Open Questions & Next Steps

1. **CRDT vs Event-Based**: Phase 1-3 use event-based edits. Phase 4 could add Yjs for real-time collaboration.
2. **Conflict Resolution**: How to handle concurrent human+AI edits? Current approach: last-write-wins with snapshots.
3. **Branching**: Support parallel versions? (parent_snapshot_id enables this, UI not implemented)
4. **Prompt Intent Parsing**: Should we parse "Revise conclusion" vs "Expand section 2"? BAML agent handles this.
5. **Real-Time Collaboration**: Multi-user editing requires Yjs or similar CRDT library.

---

## Success Criteria

- [x] Document events emitted to NATS
- [x] Projection stores document state and snapshots
- [x] Prompt bar pattern (not chat sidebar)
- [x] AI edits document via tool calls
- [x] Snapshots created per turn
- [x] Accept/reject workflow for AI suggestions
- [x] Diff visualization between versions
- [ ] Real-time collaboration (deferred to Yjs integration)

---

**End of Runbook**
