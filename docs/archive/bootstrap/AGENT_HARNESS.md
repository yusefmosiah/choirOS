# Director + Associate Agent Harness

> Two Ralph loops, two sandboxes, one task protocol.

---

## Core Insight

The Director plans and supervises. The Associate executes deterministically.
All state changes are expressed as Associate tasks, including git actions.

## Roles

### Director (planner)
- Receives user prompts.
- Expands intent into tasks.
- Evaluates Associate results and decides next actions.
- Uses Bedrock models and a small toolset.

### Associate (executor)
- Runs Vite and the ChoirOS UI.
- Edits repo, runs commands, and verifies results.
- Returns structured diffs, logs, and verification status.

## Prompt Flow

User -> Associate UI -> Director -> Associate task -> Associate verify -> Director

## Task Protocol

See `docs/ralph/CONTRACTS.md` for full schemas. High-level task kinds:
- edit_repo
- run
- git
- inspect

## Verification

Default: "smoke" verification when discoverable. If no obvious checks are
available, the Associate reports verify.status = "unknown" and asks for input.

## Sandboxes

Each user session spawns:
- 1 Director sandbox
- 1 Associate sandbox

No secrets live in either sandbox. The control plane is a separate repo and
runtime, not mounted into the sandboxes.
