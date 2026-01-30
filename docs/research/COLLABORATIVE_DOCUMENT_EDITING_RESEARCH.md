# Collaborative Document Editing: Research & Architecture

**Date**: 2026-01-30
**Context**: Chat is the control plane; Writer and other apps are projections over the same tool-call ledger.

**Update Note (2026-01-30)**: The attempt to eliminate chat and replace it with a single non-chat interface
did not work. The new direction keeps **Chat as the go-to app**, while **deprecating the linear message list
as the primary context model**. The system should **document all tool calls** and let other apps (Writer,
Context Heatmap, Runmap, Audit, Mail) render those tool calls and resulting state in different views. The
prompt bar is a shortcut into the Chat app at the center of ChoirOS.

---

## Part 1: The Core Pattern

### What You're Building

**Chat as Control Plane (not removed, re-centered)**

```
┌─────────────────────────────────────────────────────────────┐
│               Chat App (Hub + Tool-Call Ledger)             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  User: Write a blog post about AI                          │
│  AI: [Invokes tools: document.create, document.edit...]     │
│  User: Make it longer                                      │
│  AI: [Invokes tools: document.edit...]                      │
│  User: Add a section about X                                │
│  AI: [Invokes tools: document.edit...]                      │
│                                                               │
│  → Tool-call ledger is the source of truth                  │
│  → Messages are a view, not the model                        │
│  → Chat spawns and controls other apps                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│           Writer App (Projection of Chat + Tools)            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Document: "My Blog Post"                              │    │
│  │                                                        │    │
│  │ Introduction                                          │    │
│  │ The rapid advancement of AI in 2026 has...         │    │
│  │ [User edits inline]                                   │    │
│  │                                                        │    │
│  │ Section: Technical Details                            │    │
│  │ [AI generates this section...]                         │    │
│  │ [User selects text, asks: "Simplify this"]          │    │
│  │ [AI revises selected text...]                          │    │
│  │                                                        │    │
│  │ Conclusion                                             │    │
│  │ [AI generates...]                                     │    │
│  │ [User asks: "Make it punchier"]                         │    │
│  │ [AI rewrites entire conclusion...]                     │    │
│  │                                                        │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  Prompt: [Revise the conclusion to be more compelling    │    │
│          ___submit___                                      │
│                                                               │
│  → Document is the focus                                   │
│  → Prompt routes to Chat (tool-call source)                 │
│  → Edits happen in-place, not appended                      │
│  │
└─────────────────────────────────────────────────────────────┘
```

### The Generalization

This pattern **treats chat as the hub** and all other apps as **views over the same tool-call stream**:

| App Type | Primary Content | Prompt Behavior | Role |
|-----------|-----------------|------------------|------|
| **Chat (Hub)** | Tool-call ledger + summary | Routes to tools | Orchestrator |
| **Writer** | Document | Inline edit / rewrite | Projection |
| **Context Heatmap** | Context graph | Highlight usage | Projection |
| **Runmap** | Execution graph | Trace steps | Projection |
| **Audit** | Tool-call log | Explain provenance | Projection |
| **Mail** | Thread | Append | Projection |
| **Terminal** | History | Append | Projection |

All use the **prompt bar at bottom** pattern. The difference is what the prompt does to the content and
how it maps back into the **shared tool-call ledger**.

---

## Part 2: Technical Foundations

### Collaborative Editing: CRDTs vs OT

The research shows two main approaches:

**Operational Transformation (OT)**
- What Google Docs uses (historically)
- Central server transforms operations
- Complex, but proven at scale
- Example: "Two users type 'hello' → server reconciles"

**CRDTs (Conflict-Free Replicated Data Types)**
- Modern approach, gaining adoption
- No central server needed (theoretically)
- Libraries: Yjs, Automerge, Loro
- Each user has local copy, changes merge automatically

**For ChoirOS**, the research suggests:
- **CRDTs are simpler** for local-first + event sourcing
- **Yjs** is the most mature (used in many products)
- **Automerge** is good for JSON documents (your event model!)

### The Hybrid Approach: Event Sourcing + CRDTs

**Key Insight**: You can have BOTH:

```
┌─────────────────────────────────────────────────────────────┐
│                    EVENT SOURCING (NATS)                     │
│  - Immutable log of all operations                         │
│  - Supports replay, audit, debugging                        │
│  - "What happened and when?"                                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    PROJECTION (libsql)                      │
│  - Materialized current state                                │
│  - Fast queries for UI                                        │
│  - "What's the state now?"                                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    REAL-TIME SYNC (Yjs/CRDT)                 │
│  - Collaborative editing (human + AI)                       │
│  - Conflict resolution                                       │
│  - "How do we edit together?"                                 │
└─────────────────────────────────────────────────────────────┘
```

**They solve different problems:**
- **Event sourcing**: History, replay, audit, debugging
- **CRDTs**: Real-time collaboration, conflict resolution

### Why This Matters for AI + Human Editing

**The AI Editing Problem**:
1. User selects text → AI generates replacement
2. Meanwhile, user edits another part of document
3. Which wins? How do we merge?

**The Solution**:
- Treat AI edits as "operations" in the CRDT
- User edits are also operations
- CRDT merges them automatically
- Event sourcing logs all operations (for replay)

---

## Part 3: Event Model for Documents

### Event Types for the Writer App

```python
# Document lifecycle events
document.create
document.snapshot
document.restore

# Edit events (these become CRDT operations)
text.insert(position, content)
text.delete(start, end)
text.replace(start, end, content)

# AI-specific events
ai.suggestion(document_id, suggestion_id, diff)  # AI proposes edit
ai.suggestion.accept(suggestion_id)                 # User accepts
ai.suggestion.reject(suggestion_id)                 # User rejects
ai.inline_edit(position, content)                    # AI edits directly

# Turn management
turn.start(user_id, context)
turn.end(user_id, result_snapshot_id)
turn.branch(user_id, parent_turn_id)  # "Try a different path"

# Cursor/selection (for collaboration)
cursor.move(user_id, position)
selection.set(user_id, start, end)

# Chat + tool-call ledger (source of truth)
chat.message.create
tool.call
tool.result
app.spawn
app.focus
app.view.sync
```

### The Snapshot Strategy

**When to Snapshot?**
1. **Every turn** - Before AI acts, snapshot current state
2. **After major edits** - AI rewrites a section
3. **User manual** - "Save version" action

**Snapshot Contents:**
```python
{
    "snapshot_id": "uuid",
    "document_id": "doc_123",
    "parent_snapshot_id": "uuid",  # For branching
    "timestamp": "2026-01-29T...",
    "content": {
        "title": "My Blog Post",
        "sections": [...]  # OR raw text, OR CRDT state
    },
    "metadata": {
        "turn_number": 5,
        "author": "user_or_ai",
        "word_count": 1234,
        "tags": ["draft", "ai-assisted"]
    }
}
```

**Reverting to a Snapshot:**
```python
# User clicks "Go back to turn 3"
restore_event = {
    "type": "document.restore",
    "snapshot_id": "turn_3_snapshot",
    "reason": "user_manual_revert"
}

# Projector applies this as:
# 1. Load snapshot content
# 2. Emit as current document state
# 3. Update turn_number
```

---

## Part 4: UI/UX Patterns from 2026 Tools

### Gemini Canvas (Google, 2025)

**What they did:**
- Prompt bar at bottom (no box, merges with screen)
- "Canvas" mode for documents (separate from chat)
- Real-time collaborative editing
- AI generates, user edits inline
- Can export to Docs when done

**Key patterns:**
```
┌─────────────────────────────────────────────────────────────┐
│  [Canvas mode]                                               │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │ Document content (editable)                           │     │
│  │                                                        │     │
│  │ [AI generates section...]                              │     │
│  │ [User can edit anywhere]                               │     │
│  │                                                        │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  [Select "Canvas" in prompt bar]                             │
│  ┌────────────────────────────────────────────────────┐     │
│  │ [prompt bar]                                       │     │
│  │ [Tools: • 📎 Attach • 🎨 Style • ⚡ Generate] │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Cursor AI (2025-2026)

**What they did:**
- AI code editor, not chat-first
- Tab completion for suggestions
- "Composer" mode for multi-step changes
- Visual editor for UI components
- Inline diffs for AI suggestions

**Key patterns:**
- AI suggestions show as inline diffs
- User can "Tab" to accept, keep typing to reject
- Can highlight code, ask AI to modify it
- "Composer" = multi-operation prompt

**Relevant to Writer:**
- Inline edits with diff visualization
- "Accept/Reject" workflow
- Multi-step operations (e.g., "refactor this section")

### Adobe Acrobat + AI (2025-2026)

**What they did:**
- Prompt bar in PDF editor
- "Generate summary" → adds to document
- "Rewrite section" → inline edit
- AI assistant in sidebar

**Key patterns:**
- Prompt bar is modal (opens when needed)
- AI operations map to document actions
- Can undo/redo AI edits

---

## Part 5: The "Prompt Bar" Mental Model

### Chat as Hub, Views as Projections

**Chat App (Hub view):**
```
┌─────────────────────────────────────────────────────────────┐
│  Chat with AI                                                 │
│                                                              │
│  User: Write a blog post                                    │
│  AI: [Calls document.create + document.edit]                │
│  User: Make it longer                                       │
│  AI: [Calls document.edit]                                  │
│                                                              │
│  [prompt]                                    [Send button]      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
Mental model: "I'm issuing requests; tools run and update views"
```

**Writer App (Projection view):**
```
┌─────────────────────────────────────────────────────────────┐
│  My Blog Post                                            [v5 ▼]       │
│  ┌────────────────────────────────────────────────────┐   │
│  │ [Document content - editable]                        │   │
│  │                                                      │   │
│  │ Introduction                                         │   │
│  │ [User edits this text directly]                      │   │
│  │                                                      │   │
│  │ [AI suggestion: "Add more detail..." (diff view)]   │   │
│  │ [Accept] [Reject]                                    │   │
│  │                                                      │   │
│  └────────────────────────────────────────────────────┘   │
│                                                              │
│  [v] View turn history                                     │
│                                                              │
│  What should I do with this section?                       │
│  [Revise] [Expand] [Simplify] [___More___]                 │
│  ┌────────────────────────────────────────────────────┐   │
│  │ [prompt bar]                            [Send]     │   │
│  └────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
Mental model: "I'm editing a document; the prompt bar routes to Chat"
```

### The Key Distinctions

| Aspect | Chat Hub | Writer View |
|--------|----------|------------|
| **Primary focus** | Tool-call ledger + summary | Document |
| **Prompt result** | Tool calls + results | Document change |
| **History** | Tool-call timeline | Turn snapshots |
| **Mental model** | Orchestration | Co-editing |
| **AI role** | Operator | Collaborator |
| **User control** | Command routing | Full control (edit anywhere) |

### Prompt Bar Operations

**For Writer, the prompt bar should support:**

**Text Operations:**
- "Revise the conclusion to be more compelling"
- "Expand section 2 with more examples"
- "Simplify this paragraph" (with text selected)
- "Rewrite the entire document in a more formal tone"

**Navigation:**
- "Go back to version 3"
- "Compare version 3 and current"
- "Branch from version 5"

**Meta-operations:**
- "What are the main points of this document?"
- "Generate an outline based on this"
- "Find citations for [claim]"

**The key**: All of these are TOOLS. The prompt bar routes to Chat, which documents the tool calls and
fans results out to other app views.

---

## Part 6: Architecture Proposal

### Event-Sourced System with Chat Hub

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (React)                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  ChatApp (Hub)                                       │    │
│  │    - Tool-call ledger timeline                      │    │
│  │    - Prompt bar routes to tools                     │    │
│  │    - Spawns/controls other apps                     │    │
│  │                                                     │    │
│  │  Writer / Heatmap / Runmap / Audit (Views)          │    │
│  │    - Subscribe to tool-call ledger                  │    │
│  │    - Render domain-specific projections             │    │
│  └─────────────────────────────────────────────────────┘    │
│                         ↕ WebSocket (NATS)                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Chat + Tool Ledger Service                           │    │
│  │    - POST /chat/messages                              │    │
│  │    - POST /tools/call                                 │    │
│  │    - GET /ledger/{session_id}                         │    │
│  │                                                       │    │
│  │  Document Service                                     │    │
│  │    - POST /documents/{id}/edit                        │    │
│  │    - POST /documents/{id}/prompt                      │    │
│  │    - GET /documents/{id}/versions                     │    │
│  │    - POST /documents/{id}/restore/{version_id}        │    │
│  │                                                       │    │
│  │  Emits events to NATS                                  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 ORCHESTRATOR (Run Orchestrator)               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  State: session_state, tool_calls, view_context      │    │
│  │                                                       │    │
│  │  Actions:                                             │    │
│  │    - parse_prompt: Understand user intent             │    │
│  │    - select_operation: tool routing                   │    │
│  │    - execute_tool: Generate edits / calls             │    │
│  │    - create_snapshot: Save version                    │    │
│  │                                                       │    │
│  │  Transitions:                                         │    │
│  │    - idle → processing → done → idle                  │    │
│  │                                                       │    │
│  └─────────────────────────────────────────────────────┘    │
│                         ↕ Emits events                       │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    EVENT LOG (NATS JetStream)                 │
│  - chat.message.create                                    │
│  - tool.call                                              │
│  - tool.result                                            │
│  - app.spawn                                              │
│  - app.focus                                              │
│  - document.{id}.create                                   │
│  - document.{id}.edit.{seq}                               │
│  - document.{id}.snapshot.{version_id}                    │
│  - document.{id}.restore.{version_id}                     │
└──────────────────────────┬──────────────────────────────────┘
                          │ Projector reads
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    PROJECTION (libsql)                        │
│  Tables:                                                    │
│  - tool_calls (id, session_id, tool, args, result, ts)      │
│  - documents (id, current_content, current_version)        │
│  - document_snapshots (id, version_id, content, metadata)   │
│  - document_edits (id, edit_seq, operation, diff)           │
│  - ai_suggestions (id, suggestion_id, diff, status)         │
└─────────────────────────────────────────────────────────────┘
```

### Real-Time Collaboration Layer (Yjs)

```javascript
// Frontend: Yjs integration
import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';

const doc = new Y.Doc();
const text = doc.getText('document-content');

// Connect to NATS/WebSocket
const provider = new WebsocketProvider(
  `wss://localhost:8080/documents/${docId}`,
  doc
);

// User edits locally (optimistic)
text.insert(start, content);

// Syncs via WebSockets to other clients
// Backend logs to NATS for event sourcing

// AI edits come as events
provider.on('ai-edit', (edit) => {
  text.apply(edit.diff);  // Yjs handles merge
});
```

---

## Part 7: Concrete Implementation Plan

### Phase 1: Document Events (Event Sourcing)

**PREDICTION**: Documents can be reconstructed from NATS events.

**EXPERIMENT**:
1. Emit `document.create`, `document.edit` events
2. Store in libsql via projector
3. Query document state from projection

**OBSERVE**:
- Event count in NATS matches row count in libsql
- Document content reconstructable from events

### Phase 2: Snapshot & Turn Management

**PREDICTION**: Users can navigate turns and restore snapshots.

**EXPERIMENT**:
1. Create snapshot on turn start
2. Store snapshot_id with each edit
3. Restore to previous turn via event

**OBSERVE**:
- `document.snapshots` table has turn history
- `document.restore` event reverts document state

### Phase 3: AI Edits as CRDT Operations

**PREDICTION**: AI and human edits merge correctly.

**EXPERIMENT**:
1. User edits while AI is "thinking"
2. Both emit as `document.edit` events
3. Projector applies in NATS sequence order
4. Frontend Yjs merges for real-time

**OBSERVE**:
- No data loss
- Final state consistent across clients
- Event log shows both edits

### Phase 4: Prompt Bar as Chat Routing

**PREDICTION**: Prompt bar routes to Chat, which logs tool calls and updates document views.

**EXPERIMENT**:
1. User types: "Revise conclusion"
2. System emits `chat.message.create`
3. Orchestrator emits `tool.call` and `tool.result`
4. Document changes via `document.edit`
5. Writer view updates from the ledger

**OBSERVE**:
- Document content changed
- Tool-call ledger shows the edit and result
- Prompt bar clears

### Phase 5: Version History UI

**PREDICTION**: Users can navigate and compare versions.

**EXPERIMENT**:
1. Click version slider → show snapshot
2. "Compare with current" → show diff
3. "Restore this version" → emit `document.restore` event

**OBSERVE**:
- UI shows snapshot content
- Diff visualization works
- Restoration updates current document

---

## Part 8: How This Generalizes

### The Prompt Bar Pattern

All apps use the same pattern:

```
┌─────────────────────────────────────────────────────────────┐
│  [App Window]                                    [v3 ▼] [☰]     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ [App-specific content area]                           │    │
│  │  - Writer: document                                 │    │
│  │  - Mail: message thread                             │    │
│  │  - Terminal: command history                         │    │
│  │  - Files: file browser                              │    │
│  │                                                      │    │
│  │  [AI edits and suggestions appear inline]           │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  [prompt bar with context-aware suggestions]   [Send]     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### What Changes Per App

| App | Content | Prompt Operations | Edit Behavior |
|-----|---------|-------------------|---------------|
| **Chat (Hub)** | Tool-call ledger | Route + summarize | Tool calls |
| **Writer** | Document | Revise, expand, rewrite | Inline edits |
| **Mail** | Thread | Reply, forward, summarize | Append |
| **Terminal** | History | Command, explain | Append |
| **Files** | Browser | Search, filter | None (read-only) |

**The universal interface:**
- Prompt bar at bottom (routes to Chat)
- Context-aware (knows what's selected)
- AI edits appear inline
- Version/snapshot control

---

## Part 9: Open Questions & Research Needs

### Questions for Further Investigation

1. **Tool-Call Ledger as Source of Truth**
   - What is the minimal schema for tool.call + tool.result?
   - How should other apps subscribe and reconcile?

2. **Snapshot Granularity**
   - Snapshot every turn? Every N operations?
   - How to handle branching (parallel explorations)?

3. **AI Edit Conflicts**
   - User deletes paragraph while AI is rewriting it
   - How to present conflict to user?
   - Can AI "see" user edits in real-time?

4. **Diff Visualization**
   - How to show AI suggestions (inline diff? side-by-side?)
   - What if AI rewrites entire document?
   - How to show "this is turn 5 vs turn 3"?

5. **Real-Time Collaboration**
   - Multiple humans + AI editing together
   - Yjs handles this well
   - How does the tool-call ledger reflect CRDT ops?

### What to Prototype First

1. **Chat hub + tool-call ledger**
   - Chat is the default app
   - Tool calls are logged and queryable
   - Other apps subscribe to tool-call events

2. **Writer as projection**
   - Document stored as events
   - Snapshots per turn
   - Prompt bar routes to Chat, edits emitted as tools
   - Version navigation

3. **Add real-time sync**
   - Yjs for collaborative editing
   - Websocket provider to NATS
   - Tool-call ledger records CRDT ops

4. **Multi-app generalization**
   - Apply pattern to Mail, Terminal, Files, Heatmap, Runmap, Audit
   - Each app defines its content model and operations
   - Shared prompt bar component

---

## Part 10: References

### CRDTs & Collaborative Editing
- [CRDTs vs Operational Transformation: A Practical Guide](https://hackernoon.com/crdts-vs-operational-transformation-a-practical-guide-to-real-time-collaboration)
- [Best CRDT Libraries 2025](https://www.velt.dev/blog/best-crdt-libraries-real-time-data-sync)
- [Yjs GitHub](https://github.com/yjs/yjs)
- [Automerge](https://automerge.org/)

### AI Writing Tools (2026)
- [Gemini Canvas Features](https://blog.google/products-and-platforms/products/gemini/gemini-collaboration-features/)
- [Cursor AI Features](https://cursor.com/features)
- [Adobe Acrobat AI Features](https://helpx.adobe.com/acrobat/desktop/whats-new/whats-new-acrobat-desktop.html)

### Event Sourcing & CQRS
- [Event Sourcing for AI Agents](https://www.cursor.com/features) (pattern recognition)
- NATS JetStream documentation
- libsql / Turso for edge databases

---

**End of Document**
