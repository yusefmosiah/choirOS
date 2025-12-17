# ChoirOS: Build Phases

> Outside-in. Interface → Sources → Platform → Publishing → Collective.

---

## Phase 0: Bootstrap ✓

**Goal:** Crystallize decisions without writing code that buries them.

**Artifacts:**
- [x] DECISIONS.md — What we've chosen and why
- [x] UNKNOWNS.md — What we're explicitly deferring
- [x] PHASES.md — This document

**Exit criteria:** Someone else (human or agent) can read these docs and build Phase 1.

---

## Phase 1: Static Shell ✓

**Goal:** A working desktop in the browser. No backend. No persistence. Just the shape.

**Deliverables:**
- [x] Vite + React + TypeScript project scaffold
- [x] Desktop component (wallpaper, icon grid)
- [x] Window component (drag, resize, minimize, maximize, close, focus)
- [x] Taskbar component (? bar input, app tray)
- [x] Writer app (BlockNote editor)
- [x] Files app
- [x] Mobile-responsive windows with touch support

**Exit criteria:**
- Can open Writer window from desktop icon
- Can drag/resize window
- ? bar captures input
- Writer accepts content

---

## Phase 2: Sources Workflow ✓

**Goal:** Users can ingest external content as artifacts.

**Deliverables:**
- [x] FastAPI backend with parsers
- [x] YouTube transcript extraction
- [x] Web page content extraction
- [x] Document parsing (PDF, DOCX, PPTX, etc.)
- [x] ? bar URL detection and parsing
- [x] File upload via ? menu
- [x] Artifacts appear in Files app
- [x] Open artifacts in Writer

**Exit criteria:**
- Paste URL in ? bar → content extracted → artifact created
- Upload file via ? menu → parsed → artifact created
- View and edit artifacts in Writer

**Note:** The ? bar at this phase is a **utility bar**, not a prompt box. Users don't need to "prompt engineer" — just paste a URL. Power users can explore the ? menu for more features.

---

## Phase 3: Agent Platform 🔜

**Goal:** The agentic infrastructure. MicroVM sandbox where the shell itself runs, modifiable at runtime.

### Why Sandbox-First?

The key insight: **everything built so far should run inside the agent sandbox**. This means:
- The desktop shell is served from a microVM
- Agents can modify the shell files (CSS, components, layout)
- Vibecoding works: user prompts → agent edits → Vite HMR → live update

### Subtasks

**3.1: MicroVM Base Image**
- [ ] Firecracker VM with Alpine + Node + Vite
- [ ] Choir shell source in `/app`
- [ ] Artifacts directory at `/artifacts`
- [ ] Vite dev server running

**3.2: VM Orchestration**
- [ ] Spawn VM on user connect
- [ ] WebSocket bridge (browser ↔ VM)
- [ ] Destroy on disconnect (or idle timeout)

**3.3: S3 State Sync**
- [ ] Artifacts sync to S3
- [ ] Restore on VM spawn
- [ ] Per-user namespacing

**3.4: NATS Event Bus**
- [ ] JetStream setup
- [ ] Action log streaming
- [ ] Agent subscriptions

**3.5: Agent Harness**
- [ ] Agent receives ? bar input
- [ ] Agent can read/write files
- [ ] Agent actions visible (opens windows, edits files)

### Launch Feature: Vibecoding

The proof point for Phase 3: **type in ? bar → agent modifies theme/layout → UI updates live**.

This demonstrates:
- Agent can modify the shell
- Changes are visible and immediate
- Users can "vibe" the system into their preferred state

**Exit criteria:**
- Browser connects to microVM (not local dev server)
- ? bar input reaches agent
- Agent can write files, UI updates via HMR
- "Change the background to dark blue" works

---

## Phase 4: Persistence

**Goal:** State survives sessions. Local-first with cloud sync.

**Deliverables:**
- [ ] SQLite in VM (`/state/db.sqlite`)
- [ ] Artifacts stored in SQLite + synced to S3
- [ ] Action log persisted
- [ ] Export workspace (download db + artifacts)
- [ ] Import workspace

**Exit criteria:**
- Close browser, reopen → artifacts restored
- Can download workspace as backup
- Can import workspace on new session

---

## Phase 5: Publishing

**Goal:** Artifacts become shareable. Citation graph emerges.

**Deliverables:**
- [ ] Public artifact publishing
- [ ] Citation metadata (artifact A cites artifact B)
- [ ] Citation graph queries
- [ ] Export as standalone document (with citations)

**Exit criteria:**
- Can publish artifact to public URL
- Citations tracked and queryable
- Export includes provenance

---

## Phase 6+: Collective Intelligence

Beyond core product. Requires Phase 5 stable.

- Global NATS mesh
- Cross-user citation and discovery
- Citation rewards (USDC micropayments)
- CHIP token governance
- Custom domains as identity

---

## Dependencies

```
Phase 0 (decisions)
    ↓
Phase 1 (shell) ✓
    ↓
Phase 2 (sources) ✓
    ↓
Phase 3 (platform) ← YOU ARE HERE
    ↓
Phase 4 (persistence)
    ↓
Phase 5 (publishing)
    ↓
Phase 6+ (collective)
```

---

## The ? Bar Philosophy

The ? bar is the **utility bar**, not a chatbot input.

| User Type | Experience |
|-----------|------------|
| **Casual** | Paste URL → get parsed content. Click ? → see menu. |
| **Power** | Type natural language commands. NL CLI for everything. |

**Key UX constraint:** Users should NOT need to know the right prompt. The point of ChoirOS is to move beyond prompt engineering. Simple actions are discoverable via GUI; complex actions are accessible via natural language.

---

## Velocity Check

Each phase should take **1-2 weeks** of focused work.

If a phase takes longer:
- Scope was too big → split it
- Unknown became a blocker → promote to decision
- Decision was wrong → revise and document why

---

*Last updated: 2025-12-17*
*Status: Phase 3 in planning*
