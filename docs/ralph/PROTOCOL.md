# Ralph-in-Ralph Protocol (v1)

This protocol defines the interaction between the **Director** (planner/verifier) and the **Associate** (executor) in the ChoirOS system.

**Core Invariant**: All state is durable. Ground truth lives on disk. No agent relies on chat history.

## 1. Artifacts

The system operates by exchanging three primary types of artifacts on the filesystem.

### A. Task Contract (Director-Authored)
Path: `tasks/T-{id}.yaml`
Schema: `tasks/schema.json`

A persistent definition of work to be done.
- **Objective**: Natural language description.
- **Scope**: Allowed/disallowed files and tools.
- **Verification**: Explicit commands to run to prove success.
- **Acceptance Criteria**: Checklist for the Director to verify.
- **State**: `open` | `proposed` | `done` | `failed`.

### B. Evidence Bundle (Associate-Authored)
Path: `evidence/T-{id}/run-{run_id}/`
Schema: `evidence/manifest.schema.json`

A durable record of an execution attempt.
- **Manifest**: `manifest.json` containing metadata, decision, and summary.
- **Logs**: `checks/` containing stdout/stderr of verification commands.
- **Provenance**: `provenance/` containing environment info, tool versions, and git commit hashes.
- **Diff**: `diff.patch` (optional) capturing the changes made.

### C. Skill Result (Skill-Authored)
Path: `skills/results/{run_id}/` (transient or persistent)

Structured output from a specific skill (e.g., Reviewer, QA).
- **Manifest**: Input/Output pairs adhering to `skills/{skill_name}/io_schema.json`.

## 2. The Loop

### Step 1: Director Plans
The Director reads the user request and repo state. It creates or updates a Task Contract (`T-001.yaml`) with status `open`.

### Step 2: Associate Executes (Ralph Loop)
The `associate_loop` wrapper sees the `open` task.
1.  **Context**: Loads the Task Contract and allowed file subsets.
2.  **Work**: Uses the LLM/Tools to edit code and run internal tests.
3.  **Self-Verify**: Runs the `verification_commands` specified in the Task.
4.  **Emit Evidence**: Writes the `evidence/T-001/run-001/` bundle.
5.  **Propose**: If successful, updates Task status to `proposed`. If failed, leaves as `open` (or `failed` if retries exhausted).

### Step 3: Director Verifies
The `director_loop` sees the `proposed` task.
1.  **Read Evidence**: Inspects the Evidence Bundle (logs, diffs).
2.  **Verify**: May run its own checks or delegate to a "Reviewer" skill.
3.  **Decide**:
    *   **Accept**: Merges the changes (if in a branch) and marks Task `done`.
    *   **Reject**: Updates Task with feedback and resets status to `open`.

## 3. Schemas

See `tasks/schema.json` and `evidence/manifest.schema.json` for rigorous definitions.
