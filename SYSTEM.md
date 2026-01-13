# System Charter

## Mission
To build a general-purpose coding agent composed of a Director agent (planner/verifier) and Associate agents (executors) that run in deterministic loops, producing durable, versioned evidence of their work.

## Invariants

1.  **Ground Truth Lives on Disk**
    *   No agent relies on chat history or ephemeral memory.
    *   All context must be reconstructible from the filesystem (Tasks, Evidence, Code).

2.  **Artifacts are Memory**
    *   Agent runs are disposable.
    *   The only durable output is an Artifact (Task Contract, Evidence Bundle, Skill Result).

3.  **Director is Verifier-of-Record**
    *   Associate may *propose* completion.
    *   Only Director may *accept*, *merge*, or mark a task *done*.

4.  **Evidence is Mandatory**
    *   Every claim ("I fixed the bug", "I ran the tests") must be backed by an Evidence Bundle stored in version control.
    *   Evidence includes logs, exit codes, and diffs.

5.  **Deterministic Control**
    *   Deterministic wrappers (not the agents themselves) own:
        *   Sandbox lifecycle
        *   Policy enforcement
        *   Schema validation
        *   Circuit breakers
        *   Provenance logging

## Threat Model

*   **Context Blowup**: Agents running too long or accumulating too much history.
    *   *Mitigation*: Fresh context every run. State passed via artifacts.
*   **Hallucinated Success**: Agent claims to have run tests but didn't.
    *   *Mitigation*: Verification commands are defined in the Task, executed by the wrapper (or logged faithfully), and reviewed by the Director.
*   **Scope Creep**: Agent modifying unrelated files.
    *   *Mitigation*: Task Contracts define explicit scope. Policy enforcement blocks writes outside scope.
*   **Infinite Loops**: Agents getting stuck in retry cycles.
    *   *Mitigation*: Circuit breakers in the wrapper (max iterations, max cost).
