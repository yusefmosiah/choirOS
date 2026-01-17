# Director <-> Associate Contracts (v0)

This document defines the task and result envelopes exchanged between the
Director and Associate sandboxes. Defaults are included to keep the loop fast
and deterministic.

## DirectorTask (Director -> Associate)

Fields:
- task_id: unique id for tracking
- kind: edit_repo | run | git | inspect
- instruction: natural language goal
- acceptance_criteria: short checklist
- base_ref: optional git ref for context
- git_action: optional verb for kind = git
- allowed_tools: tool allowlist
- egress_profile: network policy
- verify_profile: verification policy
- commands: optional explicit commands
- time_budget_s: default 300
- return: requested outputs

Task kinds (v0):
- edit_repo: change files to satisfy acceptance_criteria.
- run: execute commands without modifying files.
- git: request git_checkpoint | git_reset | git_checkout | git_status.
- inspect: read-only context gathering (files, directory listings, logs).

Example:

```json
{
  "task_id": "task-001",
  "kind": "edit_repo",
  "instruction": "Add a status badge to the taskbar.",
  "acceptance_criteria": [
    "Taskbar shows a status badge",
    "No layout regressions"
  ],
  "base_ref": "main",
  "allowed_tools": [
    "read_file",
    "write_file",
    "edit_file",
    "bash",
    "git_checkpoint"
  ],
  "egress_profile": {
    "mode": "git+pkg",
    "allowlist": []
  },
  "verify_profile": {
    "mode": "smoke",
    "commands": []
  },
  "commands": [],
  "time_budget_s": 300,
  "return": {
    "diff": true,
    "diff_format": "unified",
    "logs": true,
    "files_changed": true,
    "artifacts": []
  }
}
```

## AssociateResult (Associate -> Director)

Fields:
- task_id: echoes DirectorTask
- status: ok | needs_input | failed
- summary: what changed and why
- diff: unified diff or null
- files_changed: list of file paths
- commands_run: command list with exit codes
- verify: verification results
- questions: needed user inputs
- suggested_next: optional follow-up

Result invariants:
- Use status = "failed" if verification fails.
- Use status = "needs_input" only when user input is required to proceed.
- Never respond directly to end users; only return structured results.

Example:

```json
{
  "task_id": "task-001",
  "status": "ok",
  "summary": "Added a status badge component to the taskbar.",
  "diff": {
    "format": "unified",
    "content": "diff --git a/choiros/src/components/desktop/Taskbar.tsx ..."
  },
  "files_changed": [
    "choiros/src/components/desktop/Taskbar.tsx",
    "choiros/src/components/desktop/Taskbar.css"
  ],
  "commands_run": [
    {
      "command": "npm test",
      "exit_code": 0,
      "stdout_path": "logs/cmd_1234.txt",
      "stderr_path": null
    }
  ],
  "verify": {
    "mode": "smoke",
    "status": "pass",
    "commands": ["npm test"],
    "logs_path": "logs/cmd_1234.txt"
  },
  "questions": [],
  "suggested_next": null
}
```

## Smart Defaults

Verification:
- mode: smoke
- behavior:
  - If commands provided, run them.
  - Else run the fastest obvious check if discoverable.
  - If nothing is discoverable, return verify.status = "unknown".

Egress:
- mode: git+pkg
- allowlist: empty unless explicitly set

Git actions:
- Only via DirectorTask kind = "git" (git_reset, git_checkout, git_checkpoint).

## Prompt Routing Rules (v0)

- Prompts originate in the Associate UI and are forwarded to the Director.
- The Associate does not interpret prompts directly.
- The Director may request Associate context via inspect tasks when needed.
- Director responses are delivered back to the Associate UI for display.

## Token and Redirect Rules (v0)

- No auth tokens are exposed to the Associate sandbox.
- Prompt forwarding uses a control-plane issued, short-lived session token.
- The Associate UI does not store the token; it is injected at session start.
- Director responses are signed by the Director and verified by the Associate UI.
