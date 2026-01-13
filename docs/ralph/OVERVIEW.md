# Ralph-in-Ralph Overview

## Summary

ChoirOS runs two Ralph loops in two separate sandboxes per user:

- Director sandbox: plans, supervises, and issues tasks.
- Associate sandbox: executes tasks, edits the repo, runs commands, and verifies.

The Director never edits files directly. All state changes are expressed as
Associate task types. Time travel is git-based in v0.

## Entities

### Control Plane (trusted)
- Authenticates users (v1).
- Spawns Director + Associate sandboxes.
- Hosts a stable UI (no hot reload).
- Does not mount the ChoirOS repo.

### Director Sandbox (agentic Ralph)
- Runs a planning loop using Bedrock.
- Receives user prompts and expands them into tasks.
- Evaluates Associate results and decides next steps.
- Can request git actions via Associate tasks.

### Associate Sandbox (agentic Ralph)
- Runs the ChoirOS UI and Vite dev server.
- Executes deterministic tasks with tools.
- Produces diffs, logs, and verification results.

## Prompt Flow

User -> Associate UI -> Director -> Associate task -> Associate verify -> Director

The Associate UI is a prompt surface; prompts are forwarded to the Director.
The Director replies to the user only after the Associate reports verification.

### Sequence Diagram (v0)

```
User               Associate UI           Director           Associate
 |  prompt               |                   |                  |
 |---------------------->|                   |                  |
 |                       | forward prompt    |                  |
 |                       |------------------>|                  |
 |                       |                   | plan task        |
 |                       |                   |----------------->|
 |                       |                   |                  | execute + verify
 |                       |                   |                  |-----------------|
 |                       |                   | result           |
 |                       |                   |<-----------------|
 |                       | render response   |                  |
 |<----------------------|                   |                  |
```

### Prompt Routing Rules (v0)

- All prompt surfaces in the Associate UI forward to the Director.
- The Associate does not answer prompts directly; it acts only on tasks.
- The Director responds to the user after Associate verification.
- Director responses are rendered in the Associate UI (windows/toasts/etc.).

## Visualization

There are two frontends in the system:

- Control plane UI: trusted, stable, used to create sessions and show Director
  status/logs. It may embed Associate surfaces.
- Associate UI: the live desktop (Vite hot reload), treated as untrusted.

Default UX for v0:

1) User logs into control plane.
2) Control plane spawns Director + Associate sandboxes.
3) User is routed to the Associate desktop, optionally with a Director status
   panel from the control plane. The control plane UI is static and can be
   cached; it does not require a per-user Vite server.

## Time Travel (v0)

- Git checkpoints are the time travel mechanism.
- The Director requests git actions as Associate tasks.
- Event sourcing and filesystem snapshots are deferred.

## Defaults

- Egress defaults to git + package registries.
- Verification defaults to a fast "smoke" run when discoverable.
- All state changes are expressed as Associate tasks.
