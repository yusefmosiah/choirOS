# ChoirOS Bootstrap Documentation

> The architectural DNA for vibecoding ChoirOS from scratch.

## Vision: The Agentic Computer

**"The Model is the Kernel. The Chatbot is the CLI. The Agentic Computer is the GUI."**

ChoirOS is the missing "User Space" layer—a window manager, process scheduler, and persistence engine that protects users from the raw LLM kernel. It shifts computing from "software you operate" to "software that operates."

See `../updated.md` for the complete paradigm thesis and strategic positioning.

## What This Is

A comprehensive documentation suite that can be dropped into an empty repo to bootstrap development of ChoirOS - a distributed web desktop with isolated agent execution.

## How to Use

1. **Start vibecoding** - use docs as context for AI-assisted development

## Documents

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System overview, data flow, design decisions |
| [STACK.md](./STACK.md) | Technology choices, project structure, dependencies |
| [AUTH.md](./AUTH.md) | Passkey authentication (WebAuthn), sessions, recovery |
| [NATS.md](./NATS.md) | Event bus setup, subject hierarchy, event schemas |
| [AGENT_HARNESS.md](./AGENT_HARNESS.md) | Agent architecture, NATS coupling, persistence |
| [FIRECRACKER.md](./FIRECRACKER.md) | MicroVM setup for isolated agent execution |
| [STORAGE.md](./STORAGE.md) | SQLite schema, S3 sync, Qdrant vectors |
| [DESKTOP.md](./DESKTOP.md) | Window manager, taskbar, CSS architecture |
| [APPS.md](./APPS.md) | Writer, Files, Terminal, Command bar specs |

## Quick Start

```bash
# Create project
npm create vite@latest choiros -- --template react-ts
cd choiros

# Install dependencies
npm install zustand @tiptap/react @tiptap/starter-kit @dnd-kit/core sql.js nats.ws lucide-react

# Copy these docs
cp -r path/to/choiros-bootstrap docs/

# Start developing
npm run dev
```

## Architecture Summary

```
Browser (Shell)          AWS (Brain)
┌──────────────┐         ┌──────────────┐
│ Writer       │◄───────►│ NATS         │
│ Files        │  events │ JetStream    │
│ Terminal     │         └──────┬───────┘
│ ? bar        │                │
└──────┬───────┘         ┌──────┴───────┐
       │                 │ S3   Qdrant  │
       ▼                 │ (state)(vec) │
┌──────────────┐         └──────┬───────┘
│ sql.js       │                │
│ (local cache)│         ┌──────┴───────┐
└──────────────┘         │ Firecracker  │
                         │ (agents)     │
                         └──────────────┘
```

## Prior Art (Reference Only)

These docs in the parent directory describe earlier thinking. The architecture has evolved:

- `choir_agentic_desktop_overview.md` - Vision doc (still relevant)
- `choir_evolution_narrative.md` - Historical context (mentions daedalOS decision as history)
- `agentic_computer_position_paper.md` - Position paper (technology-agnostic)
- `CHANGELOG.md` - Project history
