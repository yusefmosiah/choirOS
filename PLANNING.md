# ChoirOS Planning Document
*Stream of consciousness → Structured roadmap*

---

## 🧠 Core Insight: Choir's First Killer Use Case

**Choir is a software development automation paradigm** — an AI that reprograms itself via version control, with users able to revert changes through a React UI.

---

## 📐 Architecture: Sandbox-in-Sandbox

```
┌─────────────────────────────────────────────────────────┐
│  TEE Cloud (AWS Nitro Enclaves)                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │  MicroVM (Firecracker)                            │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  Containers (managed by Agent)              │  │  │
│  │  │  - Compute images                           │  │  │
│  │  │  - Subagents AS containers                  │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Key question:** AWS CLI in inner sandbox? → Probably yes, with scoped IAM roles

---

## 🔄 Version Control & State Travel

Two complementary systems:

| System | Purpose | Granularity |
|--------|---------|-------------|
| **Git** | Choir image deployment, code changes | Commits |
| **NATS JetStream** | Event log, real-time state | Events |

**User-facing:** React UI with "revert" button → travels back through:
- Git commits (for code/config)
- Event log (for runtime state)

---

## 📋 Prioritized Task Breakdown

### Phase 0: Housekeeping (NOW)
- [ ] **Remove Clippy** — was a demo, "don't tempt fate"
- [ ] **Commit current state** — reconcile with 8fcaf92f
- [ ] **Improve Writer UX** — run prompts from writer, not just bottom input

### Phase 1: Version Control UI
- [ ] Git integration in React shell
- [ ] Visual commit history
- [ ] Revert button with confirmation
- [ ] Diff viewer

### Phase 2: Real Terminal + Sandbox
- [ ] Terminal → actually controls inner VM
- [ ] Container management UI
- [ ] AWS integration design

### Phase 3: Media Rich Controls
- [ ] Audio player with controls
- [ ] Video player with controls  
- [ ] Image viewer
- [ ] External embeds (YouTube, RSS/podcasts, arbitrary URLs)

### Phase 4: Filesystem Features
- [ ] **Mindmap view** of files
- [ ] **OS Connector** — mount Choir as drive
  - Windows: ? (research needed)
  - macOS: FUSE / File Provider extension
  - Linux: FUSE
  - *Pattern: 1 + 3 subagents (coordinator + platform-specific)*

### Phase 5: Multi-Agent Orchestration
- [ ] Mental models for subagent composition
- [ ] Subagents as containers pattern
- [ ] Merge conflict resolution for parallel agents
- [ ] NATS JetStream event log integration

---

## 🧩 Pattern: 1 + 3 Subagents

For cross-platform tasks:
```
┌─────────────────┐
│   Coordinator   │ ← orchestrates, merges
└────────┬────────┘
    ┌────┼────┐
    ▼    ▼    ▼
  Win  Linux  Mac   ← platform specialists
```

---

## ❓ Open Questions

1. Git vs NATS JetStream — when to use which for revert?
2. AWS CLI in inner sandbox — IAM scoping strategy?
3. Subagent merge conflicts — event sourcing? CRDTs?
4. How does container state relate to git commits?

---

## 🎯 Immediate Next Actions

1. **Read current Writer component** — understand state
2. **Remove Clippy files** — clean slate
3. **Stage a clean commit** — checkpoint before pivot
4. **Design Version Control UI component**

---

*Document created: planning session*
*Status: DRAFT — needs review and iteration*
