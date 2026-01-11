# ChoirOS Bootstrap

> Documentation-driven development for an agentic desktop.

---

## What Is This?

This is the **decision layer** for ChoirOS—a web desktop where AI operates across your workspace, not in a chat silo.

**The Thesis:** The model is the kernel, the chatbot is the CLI, and the Automatic Computer is the personal mainframe where the system can build itself.

## Core Documents

Start here. Read in order:

| Document | Purpose |
|----------|---------|
| [DECISIONS.md](./DECISIONS.md) | What we've chosen and why |
| [UNKNOWNS.md](./UNKNOWNS.md) | What we're explicitly deferring |
| [PHASES.md](./PHASES.md) | Build phases with entry/exit criteria |

## Technical Specifications

Implementation details for each subsystem:

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System overview, data flow |
| [STACK.md](./STACK.md) | Technology choices, project structure, dependencies |
| [DESKTOP.md](./DESKTOP.md) | Window manager, taskbar, CSS architecture |
| [APPS.md](./APPS.md) | Writer, Files, Terminal, ? bar specs |
| [AUTH.md](./AUTH.md) | Passkey authentication (WebAuthn) |
| [NATS.md](./NATS.md) | Event bus setup, subject hierarchy |
| [AGENT_HARNESS.md](./AGENT_HARNESS.md) | Agent architecture, isolation |
| [FIRECRACKER.md](./FIRECRACKER.md) | MicroVM setup |
| [STORAGE.md](./STORAGE.md) | SQLite, S3 sync, Qdrant vectors |

## How to Use

**For coding agents:**
1. Read DECISIONS.md, UNKNOWNS.md, PHASES.md first
2. Check DECISIONS.md for constraints before any choice
3. Check UNKNOWNS.md for things NOT to decide
4. Check PHASES.md for current scope
5. Build one phase at a time
6. Update docs as you learn

**For humans:**
1. Review DECISIONS.md for alignment
2. Flag anything that feels wrong
3. Promote UNKNOWNS to DECISIONS when you have conviction

## Quick Start

```bash
npm create vite@latest choiros -- --template react-ts
cd choiros
npm install zustand @tiptap/react @tiptap/starter-kit @dnd-kit/core sql.js nats.ws lucide-react
npm run dev
```

## Related Documents

| Location | Purpose |
|----------|---------|
| [../CONTEXT.md](../CONTEXT.md) | AI context primer (for LLM priming) |
| [../CHANGELOG.md](../CHANGELOG.md) | Project history |
| [../archive/](../archive/) | Legacy vision/narrative docs |

---

*Build order: Interface → Sources → Platform → Persistence → Publishing*

*Current phase: 3 (Agent Platform)*
