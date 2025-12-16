# Choir

**The Agentic Computer.**

> *"The Model is the Kernel. The Chatbot is the CLI. The Agentic Computer is the GUI."*

---

## Overview

Choir is an operating system layer that transforms raw AI capability into useful labor through persistent state, citation economics, and a desktop metaphor. It moves beyond the limitations of chat-based interfaces ("Blank Screen Paralysis") by providing a user space—a window manager, process scheduler, and persistence engine—that protects users from the raw kernel and manages long-running tasks.

## The Core Thesis

| Layer | Computing Analogy | AI Equivalent |
|-------|------------------|---------------|
| **Kernel** | OS kernel (syscalls) | LLM (raw probabilistic processing) |
| **Shell** | CLI (text commands) | Chatbot (synchronous, stateless) |
| **User Space** | GUI (windows, apps) | **Agentic OS** (Choir) |

Current AI interaction is stuck in the "CLI era." Choir builds the **User Space** for the agentic age.

## Key Features

*   **Intent Menu ("?")**: Replaces the Start Menu. Users type natural language intents, not commands.
*   **Vibecoding**: The OS compiles prompts into temporary scripts/GUIs on demand.
*   **Confirmation Contracts**: A safety layer showing budget, tools, and output format before agent execution.
*   **Artifact Explorer**: Stream View (event log) + Artifact View (desktop). State with provenance.
*   **GenUI**: Just-in-time generated interfaces.
*   **Citation Graph**: Tracks attribution. When AI uses your work, you get paid (Thought Bank).

## Architecture & Stack

Choir utilizes a robust stack designed for sovereignty and performance:

*   **Frontend**: Web desktop (browser-based OS GUI).
*   **Event Bus**: NATS JetStream.
*   **Agent Isolation**: Firecracker microVMs.
*   **State**: Per-user SQLite synced to S3.
*   **Vectors**: Qdrant.

## Getting Started

To get started with development, please refer to the [Bootstrap Documentation](docs/bootstrap/README.md).

Quick start (for development):

```bash
npm create vite@latest choiros -- --template react-ts
cd choiros
npm install zustand @tiptap/react @tiptap/starter-kit @dnd-kit/core sql.js nats.ws lucide-react
npm run dev
```

*(Note: These are initial commands from the bootstrap phase. Please verify with `docs/bootstrap/README.md` for the most up-to-date instructions.)*

## Documentation

For a deep dive into the philosophy, architecture, and decision-making process of Choir, please consult the `docs/` directory:

*   **[Context Primer](docs/CONTEXT.md)**: A complete conceptual overview of Choir.
*   **[Bootstrap README](docs/bootstrap/README.md)**: Technical specifications, decisions, and build phases.
*   **[Decisions](docs/bootstrap/DECISIONS.md)**: Record of architectural decisions.
*   **[Architecture](docs/bootstrap/ARCHITECTURE.md)**: System overview and data flow.
