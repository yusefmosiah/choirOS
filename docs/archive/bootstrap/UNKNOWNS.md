# ChoirOS: Unknowns Registry

> Questions we're explicitly not answering yet.
> Tracked here so they don't get buried in code.
> NATS and distributed eventing are deferred until after Ralph-in-Ralph.

---

## Classification

**🔴 Hard to reverse** — Protocol-level. Agents/users will learn these patterns.  
**🟡 Medium** — Requires refactoring but contained.  
**🟢 Easy** — Swappable without cascade.

---

## Wide-Agent Search (New Section)

### 🟡 U0: When to Fanout?

**Question:** What triggers spawn-1024-agents vs. single-agent execution?

**Candidate triggers:**
1. **Explicit user request** — "try 10 different approaches"
2. **Uncertainty detection** — agent says "I'm not sure, want me to explore?"
3. **Task type classification** — creative/search tasks auto-fanout
4. **Cost-benefit calc** — if (expected_value_of_exploration > cost_of_N_agents)

**Why it's hard:** Fanout is expensive. Wrong heuristic = waste or missed opportunities.

**Deferral reason:** Need to see what tasks users actually bring.

---

### 🟡 U0.1: Fanout Visualization

**Question:** How does wide search appear on the shared canvas?

**Options:**
1. **N windows** — literally see all agents working (overwhelming?)
2. **One "search" window** — aggregated view, expand to see individuals
3. **Background + results** — fanout is invisible, only merged result appears
4. **Tree view** — hierarchical, show branches being explored

**Tension:** The "agent working is the progress indicator" principle says show it. But 1024 windows is chaos.

**Likely answer:** Aggregated view with drill-down. "12 agents exploring → click to see each"

---

### 🔴 U0.2: Merge Strategy

**Question:** How do N agent results become one result?

**Options:**
1. **User picks** — show all N, user chooses
2. **Voting** — agents vote on each other's outputs
3. **Judge agent** — separate agent evaluates and selects
4. **Ensemble** — combine outputs (makes sense for some artifacts, not others)
5. **All survive** — no merge, user has N artifacts to browse

**Why it's hard:** This is core to whether fanout is useful. Wrong merge = noise.

**Deferral reason:** Depends heavily on task type. Creative vs. factual vs. search.

---

### 🟢 U0.3: Sandbox Granularity

**Question:** Does each fanout agent get a full microVM, or lighter isolation?

**Options:**
1. **Full VM per agent** — maximum isolation, expensive
2. **Container per agent** — lighter, still isolated
3. **Process per agent** — lightest, shared kernel
4. **Shared VM, logical separation** — cheapest, weakest isolation

**Likely answer:** Start with containers (or even processes). Fanout is about exploration, not untrusted code. Full VMs for user sessions, lighter for sub-agents.

---

### 🟡 U0.4: Fanout Cost Model

**Question:** How do we price/budget wide search?

**Options:**
1. **User sets N explicitly** — "use up to 10 agents"
2. **Cost cap** — "spend up to $X on this query"
3. **Time cap** — "you have 60 seconds, use as many agents as fit"
4. **Adaptive** — start with few, expand if promising

**Deferral reason:** Depends on billing model we don't have yet.

---

## Infrastructure

### 🟡 U1: Vite Dev Server in Production

**Question:** Hot reload in prod, or build-then-serve?

**Why it matters:** Hot reload IS vibecoding. But dev servers aren't designed for multi-tenant production.

**Options:**
1. Dev server always (accept the risk)
2. Dev server for editing, build for serving (hybrid)
3. Build-then-serve, trigger rebuild on changes (latency)

**Deferral reason:** We don't know the performance/stability tradeoffs yet. Start with dev server.

---

### 🟢 U2: VM per User vs. VM per Session

**Question:** Long-lived VMs or spawn-on-connect?

**Options:**
1. Long-lived: VM idles when user disconnects, resumes on reconnect
2. Session: Spawn on connect, destroy on disconnect, restore state from S3
3. Hybrid: Keep warm for N minutes, then destroy

**Deferral reason:** Ops optimization. Doesn't affect protocol. Start with session VMs.

---

### 🟡 U3: Base Image vs. User Artifacts Boundary

**Question:** What's platform vs. what's user-customizable?

**Current guess:**
- Base image: Shell code, runtime, Vite, React
- User artifacts: Theme, layout, app registry, user apps, user content

**Why it's hard:** 
- Too much in base → users can't customize
- Too much in artifacts → updates don't propagate, security patches are user's problem

**Deferral reason:** Need to see what users actually want to customize.

---

## Agent Architecture

### 🟢 U4: Agent Runtime Stack

**Question:** What handles ? bar input in the VM?

**Options:**
1. Direct Claude API calls (simplest)
2. LangChain agent with tools
3. MCP server(s)
4. Custom harness with NATS integration

**Deferral reason:** The artifact conventions matter more. Agent internals are swappable if artifacts are stable.

---

### 🟡 U5: GenUI Loading Mechanism

**Question:** How do `.jsx` artifacts become running components?

**Options:**
1. Vite dynamic import (requires restart/HMR)
2. In-browser Sucrase/SWC (client compile)
3. VM-side compile + serve HTML
4. Iframe sandbox per component

**Dependencies:** Security model, performance requirements, isolation needs

**Deferral reason:** Need the static shell first. GenUI is phase 2.

---

### 🟡 U6: Agent Tool Access

**Question:** What tools does the agent have?

**Minimum:**
- Write file
- Read file
- List directory

**Extended:**
- Web search
- Execute code (in VM, so safe)
- Spawn child agent
- Query vector store

**Deferral reason:** Start minimal. Expand based on what users try to do.

---

## UI/UX

### 🟡 U7: Window State Persistence

**Question:** Do window positions/sizes persist?

**Options:**
1. No persistence (windows reset each session)
2. Per-session (restore on reconnect to same VM)
3. Per-artifact (notes.md always opens at same position)
4. Per-workspace (save full window layout)

**Deferral reason:** UX preference. Easy to add later.

---

### 🔴 U8: Multi-Window Same Artifact

**Question:** Can one artifact be open in multiple windows?

**If yes:** How do we handle concurrent edits? CRDT? Last-write-wins? Lock?

**If no:** Do we focus existing window? Prevent open?

**Why it's hard:** This touches the data model. If artifacts are single-writer, the system is simpler. Multi-writer requires sync primitives.

**Deferral reason:** Start with single-window-per-artifact. Revisit when it hurts.

---

### 🟡 U9: Notification Model

**Question:** How do agent outputs surface?

**Options:**
1. Toast notifications (ephemeral)
2. Notification center (persistent queue)
3. Desktop icons (files appear)
4. Dedicated "Agent Output" window
5. Inline in ? bar (NO—this rebuilds chat)

**Deferral reason:** Need to see what kinds of outputs agents produce.

---

### 🟢 U10: Keyboard Shortcuts

**Question:** Cmd+K? Cmd+N? How do shortcuts relate to ? bar?

**Likely answer:** Shortcuts are sugar for ? bar commands. But need to define the mapping.

**Deferral reason:** Polish. Not blocking.

---

### 🟡 U11: Mobile Experience

**Question:** Does the desktop metaphor translate?

**Options:**
1. Same metaphor, responsive layout (windows become fullscreen cards)
2. Different UI, same artifacts (mobile-native shell)
3. Mobile is view-only

**Deferral reason:** Desktop-first. Mobile when the model is proven.

---

## Data Model

### 🔴 U12: Artifact Hierarchy

**Question:** Flat + path strings, or explicit parent/child relationships?

**Flat (path strings):**
```
/user/notes/today.md
/user/notes/tomorrow.md
```
- Simple, Unix-like
- Hierarchy is implicit in path parsing

**Explicit (parentId):**
```
{ id: "abc", parentId: "folder-123", name: "today.md" }
```
- Database-friendly
- Easier to query children
- More complex mutations (move = update parentId + path)

**Deferral reason:** Start with path strings. They're simpler and match mental model.

---

### 🔴 U13: Large Artifact Storage

**Question:** When is content inline vs. S3 reference?

**Options:**
1. Always inline (simple, but memory pressure)
2. Threshold (e.g., >1MB → S3)
3. Type-based (images always S3, text always inline)

**Deferral reason:** Start with everything inline (most artifacts are small). Add S3 offload when we hit memory limits.

---

### 🟡 U14: Artifact Versioning

**Question:** Do we track artifact history?

**Options:**
1. No versioning (overwrite)
2. Last-N versions (ring buffer)
3. Full history (git-like)
4. Snapshots on demand

**Deferral reason:** Overwrite is fine for MVP. History is a feature, not a requirement.

---

## Economics

### 🔴 U15: Citation Graph Structure

**Question:** How do artifacts cite other artifacts?

**Options:**
1. Inline links (`[[artifact-id]]` syntax)
2. Metadata field (`citations: [id1, id2]`)
3. Separate citation table

**Why it matters:** Citations are the knowledge compounding primitive. The structure affects query patterns.

**Deferral reason:** Need artifacts flowing before we can see citation patterns.

---

### 🔴 U16: Identity and Ownership

**Question:** How are users identified? How do we know who owns an artifact?

**Options:**
1. Passkey → user_id → artifacts have owner_id
2. Wallet signature (crypto-native)
3. Anonymous until publish (privacy-first)

**Deferral reason:** Auth is infrastructure. Single-user MVP doesn't need it.

---

## Security

### 🟡 U17: VM Network Access

**Question:** What can the user's VM reach?

**Options:**
1. No network (fully isolated, S3 sync only)
2. NATS only (event bus, no public internet)
3. Allowlisted domains (NATS + specific APIs)
4. Full internet (user's responsibility)

**Why it matters:** Agent with full internet can exfiltrate. Agent with no internet can't do web search.

**Deferral reason:** Start with NATS + Claude API only. Expand carefully.

---

### 🟡 U18: GenUI Sandboxing

**Question:** How do we isolate user-generated components?

**Options:**
1. Same React tree (no isolation, fast, dangerous)
2. Shadow DOM (style isolation, not script isolation)
3. Iframe with postMessage (full isolation, awkward communication)
4. VM-side render (server components, HTML only)

**Deferral reason:** Need GenUI working before we know isolation requirements.

---

## Platform

### 🔴 U19: Multi-Tenancy Model

**Question:** How do users share artifacts?

**Options:**
1. No sharing (single-user systems)
2. Public artifacts (anyone can read/cite)
3. Permission grants (user X can read artifact Y)
4. Shared workspaces (multiple users in same VM?)

**Why it matters:** Choir vision includes citation economy, which requires sharing.

**Deferral reason:** Single-user MVP first. Sharing is the next platform.

---

### 🟡 U20: Sync Conflict Resolution

**Question:** What if user edits while offline, then reconnects?

**Options:**
1. Last-write-wins (data loss possible)
2. Fork on conflict (user resolves)
3. CRDT merge (complex, automatic)

**Deferral reason:** Offline is edge case for MVP. Handle later.

---

## Questions That Aren't Questions

These look like unknowns but are actually decided:

| "Question" | Answer | Why |
|------------|--------|-----|
| React vs Vue vs Svelte? | React | Training data, ecosystem, TipTap |
| SQL vs NoSQL? | SQLite | Portable, single-file, queryable |
| REST vs GraphQL? | Neither—NATS + files | Event-driven, not request/response |
| Tailwind vs CSS? | CSS custom properties | Runtime-mutable theming |

---

*This document is the shadow of DECISIONS.md. Every "decided" should cast an "unknown" here, and vice versa.*
