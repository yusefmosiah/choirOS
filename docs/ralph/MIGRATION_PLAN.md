# Migration Plan: Ralph-in-Ralph (Artifact-Driven)

This document outlines the migration from the v0 "Message-Based" architecture (documented in `OVERVIEW.md` and `CONTRACTS.md`) to the v1 "Artifact-Driven" architecture.

## Diff: v0 (Current) vs v1 (Proposed)

| Feature | v0 (Message-Based) | v1 (Artifact-Driven) |
| :--- | :--- | :--- |
| **Communication** | Direct JSON "envelopes" (DirectorTask, AssociateResult). | **Files on disk** (`tasks/T-###.yaml`, `evidence/run-###/`). |
| **Persistence** | Implicit (logs/events), Git for code. | **Explicit Artifacts**: Task Contracts and Evidence Bundles are the source of truth. |
| **Verification** | "verify" field in result, implicit trust. | **Evidence Bundles** with signed/hashed logs, checks, and provenance. Director is "verifier-of-record". |
| **Wrappers** | `AgentHarness` (Python class). | **Deterministic Controllers** (`associate_loop`, `director_loop`) managing sandbox lifecycle and policy. |
| **Skills** | `AgentTools` (Python class). | **Skill Manifests** (`skills/<name>/`) with strict I/O and policy gates. |
| **State** | "Thin state" in Director memory/DirectorTask. | **Stateless Runs**: Director reads disk state, plans, writes disk state, dies. |

## Questions & Reconciliations

1.  **File-Based IPC vs. Message Passing**: The v0 architecture relied on a control plane forwarding messages. The v1 architecture posits "Ground truth lives on disk."
    *   *Reconciliation*: We will move to a file-based interface. The Control Plane or Director will write `tasks/T-xxx.yaml`. The Associate will be invoked (via a wrapper) to process that file.
    *   *Implication*: The `AssociateResult` JSON return value is replaced by the `evidence/` directory content. The wrapper might still return a status code/summary to the caller, but the *data* is on disk.

2.  **Harness Role**: `supervisor/agent/harness.py` is a generic loop.
    *   *Reconciliation*: We will refactor or wrap `harness.py` to be the core engine driven by the `associate_loop` script. The script handles the "outer loop" (git setup, evidence collection), while `harness.py` handles the "inner loop" (LLM interaction).

3.  **Repo Structure**: `tasks/` and `evidence/` at the root.
    *   *Decision*: We will implement this structure in the target repo.

## Implementation Steps

1.  **Phase 0**: Define `SYSTEM.md` and `POLICY.yaml` (Invariants).
2.  **Phase 1**: Create directory structure and JSON schemas (`tasks/`, `evidence/`, `skills/`).
3.  **Phase 2**: Write `PROTOCOL.md` (superseding `CONTRACTS.md`) to define the artifact lifecycle.
4.  **Phase 3**: Implement `associate_loop.py` wrapper and validators.
