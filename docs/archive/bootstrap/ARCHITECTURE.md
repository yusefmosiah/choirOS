# ChoirOS Bootstrap Architecture (v0)

> Dual sandboxes, Sprites-first, control plane separate.

## Core Idea

The system is Ralph supervising Ralph:
- Director sandbox plans and supervises.
- Associate sandbox executes deterministically and runs the UI.
- Control plane is a separate app/repo that spawns sandboxes.

## System Overview

```
User Browser
    │
    ▼
Control Plane (trusted)
    │  spawn Director + Associate
    ▼
Director Sandbox (agentic Ralph)
    │  DirectorTask
    ▼
Associate Sandbox (deterministic Ralph)
    │  AssociateResult
    ▼
Git checkpoints (time travel)
```

## Why Vite in the Associate

Vite runs inside the Associate sandbox so the OS can rewrite itself live.
This is the vibecoding primitive: prompts -> edits -> HMR -> UI updates.

## Trust Boundaries (v0)

- Control plane is trusted and holds auth/secrets.
- Director/Associate sandboxes are untrusted.
- Repo access and command execution only happen in the Associate.
- Egress is set per task by the Director with tight defaults.

## Contracts

Task and result envelopes are defined in `docs/ralph/CONTRACTS.md`.

## Deferred (post-v0)

- NATS event bus and projections.
- Filesystem snapshots and forking.
- Firecracker/TEE isolation.
- Distributed CI/CD pipelines.

*Supersedes earlier NATS-first architecture drafts.*
