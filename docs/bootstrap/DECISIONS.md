# ChoirOS: Decision Log

> Documentation-Driven Development. Domain-Driven Design.
> Say it in Saxon. Cite it in Latin. No Latin in load-bearing walls.

---

## The Thesis

**The model is the kernel. The chatbot is the CLI. The Automatic Computer is the personal mainframe.**

ChoirOS is a web desktop where:
- AI operates across your workspace, not in a chat silo
- Knowledge compounds as artifacts, not threads
- Users can reprompt the system mid-operation for styling and structural changes
- The system can be used to build itself

---

## Decided

### D1: Outside-In Build Order

**Decision:** Interface → Workflow → Publishing → Persistence → Platform

**Rationale:** The interface IS the thesis. We need to feel the claim before we wire backends. Premature persistence is premature optimization.

**Sequence:**
1. Shell (desktop, windows, ? bar, one app)
2. Workflow (intent → action → artifact loop)
3. Publishing (artifact model, export, citation stub)
4. Persistence (SQLite, sync patterns)
5. Platform (dual sandboxes, Ralph loops, git time travel)

---

### D2: MicroVM as Session Server

**Decision:** The user's microVM serves the UI. Browser is thin client.

**Rationale:**
- Vibecoding becomes "agent writes files, Vite rebuilds, browser updates"
- Arbitrary code runs in VM, not browser (security)
- True filesystem means artifacts are just files
- The user's VM contains Choir source—building Choir in Choir becomes literal

**Architecture:**
```
Browser (thin client)
    ↓ WebSocket
Associate Sandbox
    ├── /app (Choir source, Vite project)
    ├── /artifacts (user's files, configs, GenUI)
    ├── /workspace (user files)
    ├── Vite dev server
    └── Associate agent runtime
    ↓ DirectorTask
Director Sandbox (planner)
```

---

### D3: Everything Is an Artifact

**Decision:** Theme, layout, app registry, even components—all stored as artifacts (files) that the system reads and the agent can write.

**Rationale:** Vibecoding reduces to "agent writes artifacts, system reads artifacts." No special mutation APIs. Just Unix.

**Implication:** The artifact schema is protocol. Changes ripple. Define carefully.

---

### D4: CSS Custom Properties for Theming

**Decision:** Theming via CSS custom properties, stored in artifact (e.g., `theme.json` → injected as `--var` values).

**Rationale:** Runtime-mutable. No rebuild for color changes. Agent can edit JSON, UI updates instantly.

---

### D5: Vite + React + TypeScript

**Decision:** Standard modern stack. Not Next.js (no SSR needed when VM serves).

**Rationale:**
- Hot reload is the vibecoding primitive
- Training data density (React ecosystem)
- Simple mental model (no server/client split confusion)

---

### D6: Zustand for State

**Decision:** Zustand over Redux, MobX, signals.

**Rationale:** Minimal boilerplate. Fine-grained subscriptions. No context provider hell. Well-documented patterns.

---

### D7: TipTap for Writer

**Decision:** TipTap (ProseMirror-based) for the rich text editor app.

**Rationale:** Notion-like editing. Extensible. Markdown import/export. Mature.

---

### D8: The ? Bar Is the Utility Bar

**Decision:** Single input at bottom of screen. No chat history. Responses appear as artifacts/windows/notifications.

**What it is:**
- A utility bar, not a prompt box
- Simple actions for everyone (paste URL → parse)
- Natural language CLI for power users
- Menu access via ? button

**What it is NOT:**
- A chatbot
- A place where users need to "prompt engineer"
- A response channel (responses go to windows/files/toasts)

**Rationale:** The point of ChoirOS is to move beyond prompt engineering. Users shouldn't need to know the right commands. Simple features are discoverable via GUI; complex actions are accessible via natural language, and through the ? menu for everyone; the ? menu fills out the ? bar teaching users the right commands.

---

### D9: No Modals

**Decision:** Everything is a window. Settings, preferences, confirmations, agent workspaces—all windows.

**Rationale:** Modals are chatbot thinking—synchronous, blocking, one-topic-at-a-time. Windows are desktop thinking—persistent, arrangeable, parallel. The user can have Settings open while writing. The agent can open windows the user can watch.

**Exception:** OS-level dialogs (file picker, browser auth) we can't control.

---

### D10: Agent Uses User Primitives

**Decision:** The agent operates through the same window manager and artifact APIs the user does. No backdoor.

**Rationale:**
- Agent actions become visible (opens window, edits file, saves)
- The "progress indicator" is watching the agent work—no spinners
- User can intervene mid-action (same space, same tools)
- Action log captures both sources in one stream

**Implication:** Agent calls `openWindow()`, `editArtifact()`, `createArtifact()`—same as user clicks/edits would.

---

### D11: Shared Canvas Model

**Decision:** The desktop is a shared workspace. User and agent both manipulate windows and artifacts. Generalizes to multiuser, multiagent, multisandbox.

**Rationale:**
- Collaboration is legible (interleaved action log)
- Either party can intervene in the other's work
- Scales to many agents working in parallel (each visible)
- Scales to many users in shared space (future)

**The Progress Spin Network:** The agent working IS the progress indicator. No spinner—you watch windows open, files appear, edits happen. The activity is the feedback.

---

### D12: Wide-Agent Search (Fanout Pattern)

**Decision:** The system supports spawning N agents in parallel to explore a solution space, with merge/select at the end.

**Rationale:** Some problems benefit from breadth:
- Creative exploration (try 10 different approaches)
- Adversarial robustness (red team / blue team)
- Calibration (how consistent are answers across runs?)
- Search (each agent explores a branch)

**Architecture:** Each agent gets its own sandbox (microVM or lighter). Results merge into parent workspace. User sees the fanout as parallel windows or a "search results" artifact.

**When to use:**
- Uncertainty is high, cost of exploration is low
- Multiple valid solutions exist (creative work)
- You need confidence bounds (run same prompt N times)
- Explicit search (enumerate and evaluate)

**When NOT to use:**
- Problem has one clear path
- Latency matters more than quality
- Cost of N agents exceeds value of exploration

---

### D13: Sandbox-First Architecture

**Decision:** The shell itself runs inside the agent sandbox (microVM). The browser is a thin client.

**Rationale:**
- Vibecoding becomes literal: agent writes CSS/JSX → Vite HMR → browser updates
- The shell is modifiable at runtime—users can "vibe" their environment
- Security: arbitrary code runs in VM, not browser
- Composability: building Choir in Choir is possible

**Architecture:**
```
Browser (thin client, WebSocket only)
    ↓
MicroVM (/app contains Choir source)
    ├── Vite dev server
    ├── Agent runtime
    ├── /artifacts (user content)
    └── /state (SQLite)
```

**Launch Feature:** The proof that this works is vibecoding. User types "make the background dark blue" → agent edits theme.json → HMR fires → UI updates. This demonstrates the architecture enables live modification.

---

## Deferred (Intentionally Unknown)

### U1: Vite Dev Server in Production?

**Question:** Do we run Vite dev server for hot reload in "production," or build-then-serve?

**Tension:**
- Dev server enables true live vibecoding
- Build-then-serve is stable, predictable, cacheable

**Current stance:** Start with dev server. It's the feature, not a bug. Revisit if it becomes a problem.

**Reversibility:** Medium. Switching requires changing how we serve, but doesn't affect artifact conventions.

---

### U2: VM per User vs. VM per Session?

**Question:** When user closes laptop and reopens—same VM, or new VM with restored state?

**Tension:**
- Same VM: faster resume, but resource cost for idle VMs
- New VM: clean state, but cold start latency

**Current stance:** Defer. Start with "new VM, restore from S3." Optimize later if latency hurts.

**Reversibility:** High. This is ops/infra, not protocol.

---

### U3: What Lives in Base Image vs. User Artifacts?

**Question:** Is the shell itself in `/app` (base image, everyone gets updates) or `/artifacts` (user can fork/diverge)?

**Tension:**
- Base image: maintainability, security patches, coherent platform
- User artifacts: full customization, "your computer your rules"

**Current stance:** Defer. Start with shell in base image, theme/layout/apps in artifacts. Draw the line conservatively. Expand user territory as we understand the tradeoffs.

**Reversibility:** Low-Medium. This determines fork/update dynamics. The longer we wait, the more artifacts accumulate on one side of the line.

---

### U4: Agent Runtime Architecture

**Question:** What runs in the VM to handle ? bar input? LangChain? Raw API calls? MCP servers?

**Current stance:** Defer. The artifact conventions matter more than the agent internals. Start with the simplest thing (direct Claude API call, write files). Refactor when patterns emerge.

**Reversibility:** High, if artifact conventions are stable.

---

### U5: GenUI Component Loading

**Question:** How do user-created `.jsx` artifacts become running components?

**Options:**
- Vite dynamic import (if in /app, needs rebuild)
- In-browser compiler (Sucrase/SWC WASM)
- Iframe sandbox with message passing
- Server-side render in VM, send HTML

**Current stance:** Defer. Get static shell working first. The answer will be clearer once we see how artifacts flow.

**Reversibility:** Medium. Affects security model and performance.

---

## Conventions (Protocol-Level)

These are **hard to change** once agents and users learn them.

### C1: Artifact Directory Structure

```
/artifacts
├── system/              # Shell configuration
│   ├── theme.json       # CSS custom properties
│   ├── layout.json      # Desktop icon positions, sizes
│   ├── taskbar.json     # Taskbar contents
│   └── apps.json        # App registry (id, title, icon, entry)
├── apps/                # User-created/installed apps (GenUI)
│   └── {app-id}.jsx
└── user/                # User content
    └── {path}/{artifact}
```

**Open question:** Flat vs. nested user artifacts? Explicit types vs. mime-type inference?

---

### C2: Artifact Schema (Minimal)

```typescript
interface Artifact {
  id: string;            // UUID
  path: string;          // Virtual path: /user/notes/today.md
  name: string;          // Display name
  mimeType: string;      // MIME type
  content: string | Blob;// Inline for small, reference for large
  createdAt: number;     // Unix ms
  updatedAt: number;     // Unix ms
  metadata: Record<string, unknown>; // Extensible
}
```

**Open question:** Do we need `parentId` for hierarchy, or is path sufficient?

---

### C3: System Artifact Schemas

**theme.json:**
```json
{
  "colors": {
    "bg-primary": "#0d0d0d",
    "bg-secondary": "#1a1a1a",
    "accent": "#d4af37",
    "text-primary": "#e0e0e0"
  },
  "fonts": {
    "sans": "Inter, system-ui, sans-serif",
    "mono": "JetBrains Mono, monospace"
  },
  "radii": {
    "sm": "4px",
    "md": "8px"
  }
}
```

**apps.json:**
```json
{
  "apps": [
    {
      "id": "writer",
      "title": "Writer",
      "icon": "file-text",
      "entry": "builtin:writer",
      "defaultSize": { "width": 800, "height": 600 }
    },
    {
      "id": "files",
      "title": "Files",
      "icon": "folder",
      "entry": "builtin:files",
      "defaultSize": { "width": 700, "height": 500 }
    }
  ]
}
```

**Entry conventions:**
- `builtin:{name}` — Compiled into base image
- `artifact:{path}` — Load from user's /artifacts/apps/
- `url:{url}` — Load from remote (future)

---

### C4: Action Log Schema

```typescript
interface ActionEvent {
  id: string;
  timestamp: number;
  type: string;           // COMMAND, ARTIFACT_CREATE, WINDOW_OPEN, etc.
  payload: Record<string, unknown>;
  source: 'user' | 'agent' | 'system';
}
```

Every mutation is checkpointed or logged locally. Event streaming is deferred.

---

## Anti-Patterns to Avoid

### A1: Rebuilding Chat

If responses to ? bar input appear IN the ? bar, we've failed. The ? bar is input-only. Responses are artifacts, windows, notifications.

### A2: One-Shotting the 80%

Don't generate a large codebase in one pass. Decisions get buried. Code becomes the spec. Refactoring debt compounds. Build incrementally, with decision rationale inline.

### A3: Premature Agent Complexity

Start with the dumbest possible agent: receive input, call Claude, write files. Don't reach for LangGraph, MCP, or complex orchestration until simple breaks.

### A4: Config as Code

Theme, layout, and app registry should be JSON artifacts, not TypeScript objects. The moment config requires recompilation, vibecoding dies.

---

## Open Design Questions

### Q1: Window State Persistence

Do window positions/sizes persist? Per-session? Per-artifact?

If I open notes.md in Writer at position (100, 100), close it, reopen—same position?

### Q2: Multi-Window Same Artifact

Can I open the same artifact in two windows? What happens on concurrent edit?

### Q3: Notification Model

How do agent outputs surface when there's no relevant window? Toast? Notification center? New file on desktop?

### Q4: Keyboard-First?

Is ? bar the only input, or are there keyboard shortcuts? Cmd+K? Cmd+N? How do they relate to ? bar commands?

### Q5: Mobile

The docs mention mobile responsiveness. Does the desktop metaphor translate? Or is mobile a different UI over the same artifact layer?

---

## Glossary

| Term | Definition |
|------|------------|
| **Artifact** | A file-like object with id, path, content, metadata. The unit of persistence. |
| **? Bar** | The intent input at bottom of screen. User types natural language or commands. |
| **Shell** | Desktop + windows + taskbar. The visual container. |
| **GenUI** | Generated UI—React components written by agents, loaded at runtime. |
| **Vibecoding** | Modifying the system through natural language prompts, live, mid-operation. |
| **Base Image** | The Firecracker VM template. Contains Choir source, runtime, no user state. |
| **Session VM** | A running microVM serving one user's session. |

---

## References

- [ARCHITECTURE.md](./ARCHITECTURE.md) — System overview
- [DESKTOP.md](./DESKTOP.md) — Window manager spec
- [FIRECRACKER.md](./FIRECRACKER.md) — MicroVM setup
- [../archive/STRATEGY.md](../archive/STRATEGY.md) — Strategy (archived)
- [../CONTEXT.md](../CONTEXT.md) — AI context primer

---

*Last updated: This conversation*
*Status: Living document. Decisions may be revised as we learn.*
