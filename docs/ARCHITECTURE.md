# ChoirOS Architecture (v0)

ChoirOS is a dual-sandbox system: a Director loop supervises an Associate loop.
The control plane is a separate app/repo that spawns sandboxes and never runs
untrusted code. Vite lives inside the Associate for live rewrites.

## System Overview

```
User Browser
    │
    ▼
Control Plane (trusted, separate repo)
    │  spawn Director + Associate
    ▼
Director Sandbox (agentic Ralph)
    │  DirectorTask
    ▼
Associate Sandbox (deterministic Ralph)
    │  AssociateResult
    ▼
Git Checkpoints (time travel)
```

## Components

### Control Plane (trusted)
- Spawns Director + Associate sandboxes.
- Hosts a stable UI (no hot reload).
- Holds auth and session issuance.
- Never mounts the ChoirOS repo.

### Director Sandbox (planner)
- Receives user prompts from the Associate UI.
- Expands prompts into DirectorTask envelopes.
- Evaluates AssociateResult and decides next steps.
- Requests git actions via Associate tasks.

### Associate Sandbox (executor)
- Runs the ChoirOS UI and Vite dev server.
- Executes deterministic tasks with tools.
- Edits repo, runs commands, and verifies.
- Returns structured diffs, logs, and verification status.

## Prompt Flow

User -> Associate UI -> Director -> Associate task -> Associate verify -> Director

The Associate never answers users directly; it only executes tasks. The Director
is the sole agent that communicates results back to the user.

## Trust and Egress (v0)

- Treat both sandboxes as untrusted.
- Control plane holds credentials and secrets.
- Egress is set per task by the Director with tight defaults (git + registries).

## Time Travel (v0)

Time travel is git-based. The Director requests git actions as Associate tasks.
Event sourcing and filesystem snapshots are deferred until after Sprites.

## Contracts

Director/Associate envelopes are defined in `docs/ralph/CONTRACTS.md`.

## Deferred (post-v0)

- NATS event bus and persistent event log.
- Forking and snapshotting beyond git.
- Firecracker/TEE isolation and attestation.
- Control-plane-driven CI/CD for deployments.

## Next Steps

1. Wire Director/Associate contracts into the supervisor.
2. Add Sprites sandbox adapter and spawn flow.
3. Route prompts through the Director from the Associate UI.
4. Implement git tasks + verification defaults.
