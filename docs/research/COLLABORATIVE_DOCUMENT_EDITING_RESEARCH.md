# Collaborative Document Editing: Research & Architecture

**Date**: 2026-01-29
**Context**: Writer app pattern - prompt bar, NOT chat, human+AI co-editing with snapshot version control

---

## Part 1: The Core Pattern

### What You're Building

**NOT a Chat App**

```
┌─────────────────────────────────────────────────────────────┐
│                     Chat App (What We DON'T Want)           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  User: Write a blog post about AI                          │
│  AI: [Generates text...]                                   │
│  User: Make it longer                                      │
│  AI: [Appends more text...]                                 │
│  User: Add a section about X                                │
│  AI: [Inserts section...]                                   │
│                                                               │
│  → Linear message thread                                    │
│  → Can't edit previous messages                             │
│  → "Chat" mental model                                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   Writer App (What We WANT)                  │
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
│  → Prompt bar is tool, not the interface                  │
│  → Edits happen in-place, not appended                     │
│  │
└─────────────────────────────────────────────────────────────┘
```

### The Generalization

This pattern **includes chat as a special case**:

| App Type | Primary Content | Prompt Behavior | Example |
|-----------|-----------------|------------------|---------|
| **Writer** | Document | Inline edit / append / rewrite | Google Docs with AI |
| **Mail** | Messages | Append to thread | Gmail with AI compose |
| **Terminal** | Commands | Append to history | Shell with AI suggestions |
| **Chat** | Messages | Append to thread | ChatGPT (special case) |

All use the **prompt bar at bottom** pattern. The difference is what the prompt does to the content.

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

### What Makes It Not Chat?

**Chat App:**
```
┌─────────────────────────────────────────────────────────────┐
│  Chat with AI                                                 │
│                                                              │
│  User: Write a blog post                                    │
│  AI: Here's a blog post...                                  │
│  User: Make it longer                                       │
│  AI: [Appends to previous message]                          │
│                                                              │
│  [prompt]                                    [Send button]      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
Mental model: "I'm talking to the AI, messages appear below"
```

**Writer App:**
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
Mental model: "I'm editing a document, the prompt bar is my tool palette"
```

### The Key Distinctions

| Aspect | Chat App | Writer App |
|--------|----------|------------|
| **Primary focus** | Message thread | Document |
| **Prompt result** | New message | Document change |
| **History** | Scroll up in chat | Turn snapshots |
| **Mental model** | Conversation | Co-editing |
| **AI role** | Chat partner | Collaborator |
| **User control** | Limited (edit messages?) | Full control (edit anywhere) |

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

**The key**: All of these are TOOLS, not chat. The prompt bar is the interface to AI-powered tools.

---

## Part 6: Architecture Proposal

### Event-Sourced Document System

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (React)                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  WriterComponent                                      │    │
│  │    - Yjs/Y.Text for real-time collaboration         │    │
│  │    - Prompt bar at bottom                           │    │
│  │    - Version slider (turn history)                   │    │
│  │    - Diff viewer for AI suggestions                │    │
│  └─────────────────────────────────────────────────────┘    │
│                         ↕ WebSocket (NATS)                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Document Service                                     │    │
│  │    - POST /documents/{id}/edit                       │    │
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
│                    MACHINE (Burr State Machine)               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  State: document_state, user_request                 │    │
│  │                                                       │    │
│  │  Actions:                                             │    │
│  │    - parse_prompt: Understand user intent             │    │
│  │    - select_operation: edit/expand/rewrite/...       │    │
│  │    - execute_edit: Generate new content               │    │
│  │    - create_snapshot: Save version                     │    │
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
│  - document.{id}.create                                   │
│  - document.{id}.edit.{seq}                               │
│  - document.{id}.snapshot.{version_id}                    │
│  - document.{id}.restore.{version_id}                     │
│  - document.{id}.ai.suggestion.{id}                        │
│  - document.{id}.turn.{turn_number}                        │
└──────────────────────────┬──────────────────────────────────┘
                          │ Projector reads
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    PROJECTION (libsql)                        │
│  Tables:                                                    │
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

### Phase 4: Prompt Bar as Tool Interface

**PREDICTION**: Prompt bar maps to operations, not chat.

**EXPERIMENT**:
1. User types: "Revise conclusion"
2. System emits `document.prompt` event
3. Machine routes to Burr action
4. Burr state machine: `parse_prompt` → `select_operation` → `execute_edit`
5. Result: Document changed, NOT message appended

**OBSERVE**:
- Document content changed
- No message in a thread
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
| **Writer** | Document | Revise, expand, rewrite | Inline edits |
| **Mail** | Thread | Reply, forward, summarize | Append |
| **Terminal** | History | Command, explain | Append |
| **Files** | Browser | Search, filter | None (read-only) |

**The universal interface:**
- Prompt bar at bottom
- Context-aware (knows what's selected)
- AI edits appear inline
- Version/snapshot control

---

## Part 9: Open Questions & Research Needs

### Questions for Further Investigation

1. **CRDT vs Pure Event Sourcing**
   - Can we get away with just events (no CRDT)?
   - Or is CRDT essential for human+AI concurrent edits?

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
   - How does event sourcing fit?

### What to Prototype First

1. **Single-user writer app** (no collaboration yet)
   - Document stored as events
   - Snapshots per turn
   - Prompt bar → AI edits
   - Version navigation

2. **Add Burr for orchestration**
   - Machine state machine for prompt processing
   - Routes to different operations (expand, rewrite, etc.)
   - Emits events for each action

3. **Add real-time sync**
   - Yjs for collaborative editing
   - Websocket provider to NATS
   - Test concurrent edits

4. **Multi-app generalization**
   - Apply pattern to Mail, Terminal, Files
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
