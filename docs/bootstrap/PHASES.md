# ChoirOS: Build Phases

> Outside-in. Interface → Workflow → Publishing → Persistence → Platform.

---

## Phase 0: Bootstrap (Current)

**Goal:** Crystallize decisions without writing code that buries them.

**Artifacts:**
- [x] DECISIONS.md — What we've chosen and why
- [x] UNKNOWNS.md — What we're explicitly deferring
- [x] PHASES.md — This document

**Exit criteria:** Someone else (human or agent) can read these docs and build Phase 1 without asking "but why?"

---

## Phase 1: Static Shell

**Goal:** A working desktop in the browser. No backend. No persistence. Just the shape.

**Deliverables:**
- [ ] Vite + React + TypeScript project scaffold
- [ ] Desktop component (wallpaper, icon grid)
- [ ] Window component (drag, resize, minimize, maximize, close, focus/z-index)
- [ ] Taskbar component (? bar input, app tray, clock)
- [ ] One builtin app: Writer (TipTap, minimal)
- [ ] Theme loading from `theme.json` artifact (can be hardcoded initially)
- [ ] App registry loading from `apps.json` artifact

**Entry criteria:** DECISIONS.md and UNKNOWNS.md are stable enough to build against.

**Exit criteria:** 
- Can open Writer window from desktop icon
- Can drag/resize window
- Can type in ? bar (input captured, no response yet)
- Can type in Writer (content captured, no save yet)
- Theme colors come from artifact, not hardcoded CSS

**Not in scope:**
- Persistence
- Agent responses
- File browser
- Multiple apps

---

## Phase 2: Workflow Loop

**Goal:** ? bar input produces artifacts. The core interaction works.

**Deliverables:**
- [ ] ? bar command parsing (distinguish `?command` from natural language)
- [ ] Simple agent stub (receive input, write artifact, return)
- [ ] Artifact creation → window spawning
- [ ] Notification/toast for agent responses
- [ ] Action log (in-memory, not persisted yet)

**Entry criteria:** Phase 1 complete. Shell renders and accepts input.

**Exit criteria:**
- Type "create a note called today.md" in ? bar
- Agent creates artifact
- Writer window opens with new artifact
- Action log contains COMMAND and ARTIFACT_CREATE events

**Not in scope:**
- Real agent intelligence (stub can be simple pattern matching + Claude call)
- Persistence across page refresh
- File browser

---

## Phase 3: Publishing (Artifact System)

**Goal:** Artifacts are first-class. Can create, browse, open, export.

**Deliverables:**
- [ ] Artifact model (full schema from DECISIONS.md)
- [ ] Files app (browse artifacts, grid/list view)
- [ ] Artifact CRUD operations
- [ ] Export artifact (download as file)
- [ ] Open artifact in appropriate app
- [ ] Citation stub (artifacts can reference other artifacts via metadata)

**Entry criteria:** Phase 2 complete. Artifacts are being created.

**Exit criteria:**
- Can browse artifacts in Files app
- Can open artifact in Writer
- Can download artifact
- Can see citation links (even if not yet functional)

**Not in scope:**
- Persistence across sessions
- SQLite
- Vector search

---

## Phase 4: Persistence

**Goal:** State survives page refresh. Local-first with sync-ready architecture.

**Deliverables:**
- [ ] sql.js integration (SQLite in browser)
- [ ] Zustand stores ↔ SQLite sync
- [ ] Schema from DECISIONS.md implemented
- [ ] Action log persisted
- [ ] Artifacts persisted
- [ ] Window state persisted (optional, see UNKNOWNS.md U7)
- [ ] Export database (download workspace.sqlite)

**Entry criteria:** Phase 3 complete. Artifact system works in-memory.

**Exit criteria:**
- Refresh page → state restored
- Can download workspace.sqlite
- Can import workspace.sqlite (replaces state)

**Not in scope:**
- S3 sync
- Multi-device
- MicroVM

---

## Phase 5: Platform (MicroVM)

**Goal:** The browser connects to a microVM. Live vibecoding works.

**Deliverables:**
- [ ] Firecracker VM base image (Alpine + Node + Vite + Choir shell)
- [ ] VM orchestrator (spawn on connect, destroy on disconnect)
- [ ] S3 artifact sync (VM ↔ S3)
- [ ] Browser ↔ VM WebSocket connection
- [ ] Agent runtime in VM (receives ? bar, writes files)
- [ ] Vite HMR through WebSocket (user sees changes live)

**Entry criteria:** Phase 4 complete. Single-user local version works.

**Exit criteria:**
- User connects → VM spawns
- User types in ? bar → agent writes file → Vite rebuilds → browser updates
- User disconnects → VM destroys → artifacts persist in S3
- User reconnects → new VM → artifacts restored

**Not in scope:**
- Multi-user
- NATS global bus
- Citation economy

---

## Phase 6+: Collective Intelligence

Beyond the core product. Requires Phase 5 to be stable.

- Global NATS event bus
- Cross-user citation
- Citation rewards
- Public artifact publishing
- Identity and ownership
- Custom domains

---

## Dependencies

```
Phase 0 (decisions)
    ↓
Phase 1 (shell)
    ↓
Phase 2 (workflow)
    ↓
Phase 3 (artifacts)
    ↓
Phase 4 (persistence)
    ↓
Phase 5 (platform)
    ↓
Phase 6+ (collective)
```

No phase can skip. Each is foundation for the next.

---

## Velocity Check

Each phase should take **1-2 weeks** of focused work for a single developer (or agent).

If a phase takes longer:
- Scope was too big → split it
- Unknown became a blocker → promote to decision
- Decision was wrong → revise and document why

---

## How to Use This Document

**For coding agents:**
1. Read DECISIONS.md for constraints and rationale
2. Read UNKNOWNS.md for what NOT to decide
3. Read this document for scope
4. Build one phase at a time
5. Update all three docs as you learn

**For human review:**
- Check phase exit criteria before moving on
- If exit criteria feel wrong, revise them first
- If something was harder than expected, add to UNKNOWNS.md
