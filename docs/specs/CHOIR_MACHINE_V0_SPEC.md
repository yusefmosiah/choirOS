# Choir Machine v0 Spec
Status: DRAFT
Date: 2026-01-22
Owner: ChoirOS Core

## Decision summary
- NATS is the canonical event log; SQLite is a projection only.
- The Machine is a light-control agent with no direct tools; it orchestrates Modes.
- Modes share one harness with mode-config injection (prompt + tools + budgets + policies).
- Single-writer: only one write-capable Mode runs at a time; other Modes are read-only.
- Cross-mode sharing happens via artifacts (path + hash + span), not raw file paths.

## 1) Definitions
- Machine: the supervisor control plane that reads events, updates AHDB, selects Modes, and emits directives.
- Mode: a deterministic, capability-bounded configuration for the harness.
- ModeConfig: the injected configuration that determines tools, budgets, model policy, and output policy.
- Directive: a typed event emitted by the Machine that starts/stops/updates a Mode.
- Receipt: a typed event that records capabilities used, evidence accessed, and verifier results.
- Artifact: content stored outside git with a stable content hash; references are safe to share.

## 2) Core invariants
1) NATS is the source of truth; all state can be rebuilt from the event log.
2) The Machine does not read files, write code, or access the network directly.
3) Modes operate under explicit capability gates enforced by the tool layer.
4) Only one write-capable Mode may run at a time.
5) AHDB ASSERT updates require receipts/attestations; LLM output alone is never authority.
6) All cross-mode sharing is via artifact pointers or diff artifacts.

## 3) Mode model
ModeConfig (conceptual):
- id: string
- tool_allowlist: list[str]
- model_policy: {tier, max_tokens, escalation}
- budgets: {time_s, tool_calls, diff_bytes, files_touched}
- data_scope: {repo_read, repo_write, network, artifacts_read}
- verifier_policy: {required_verifiers, allowlist}
- output_policy: {no_copy, allowed_outputs}
- receipts_required: list[str]

Modes are not separate processes; they are separate configurations injected into a shared harness.

## 4) Machine responsibilities
- Subscribe to the event stream (NATS).
- Maintain AHDB projection and a light run registry.
- Select next Mode based on:
  - AHDB state vector
  - recent receipts and verifier outcomes
  - mode guards
  - user prompts and work items
- Emit directives to start/stop/update Modes.
- Enforce single-writer scheduling.

## 5) Mode responsibilities
- Execute tasks within its capability boundaries.
- Emit receipts for tool use, context footprint, and verifiers.
- Emit proposed AHDB deltas and explicit attestation-backed deltas.
- Emit artifacts (logs, diffs, evidence pointers) for safe cross-mode sharing.

## 6) AHDB update rules
- receipt.ahdb.delta is the only event that updates the asserted AHDB projection.
- Modes may emit proposed deltas using a proposal flag in the payload.
- Proposed deltas never update asserted AHDB until a receipt or verifier attestation supports them.

Recommended payload fields:
- authority: "proposed" | "asserted"
- delta: {assert|hypothesize|drive|believe}
- evidence: [{artifact_hash, path, span, receipt_seq}]

## 7) Artifact sharing
Artifacts are the only cross-mode sharing mechanism.
- A Mode creates artifacts (logs, diffs, extracts) and publishes pointers.
- Other Modes may read artifacts by content hash or by pointer reference.
- Raw paths in other worktrees are not used for sharing.

Minimal artifact pointer:
- artifact_hash
- path (relative to repo or external)
- span (optional)
- mime_type
- size_bytes
- origin_event_seq

## 8) Event contract extensions (v0)
These event types are required for the Machine loop:
- mode.start
- mode.stop
- mode.update
- mode.heartbeat
- receipt.mode.transition
- receipt.context.footprint (already in contract)
- receipt.ahdb.delta (already in contract; include authority field)
- artifact.create
- artifact.pointer

Event type naming stays lower-case and dot-delimited.

## 9) Concurrency model (v0)
- At most one write-capable Mode is active.
- One or more read-only Modes may run concurrently.
- The Machine may pause/stop a Mode if a higher-priority directive arrives.

## 10) Security posture (v0)
- Capability gating is enforced at the tool boundary, not by prompt alone.
- Network access is a mode capability, not a tool default.
- File writes are a mode capability, not a tool default.
- The Machine remains low-context to reduce prompt injection surface.

## 11) System prompt construction
The system prompt is dynamically generated per Mode using:
- ModeConfig
- AHDB state (asserted + relevant proposed)
- Recent receipts and constraints
- Artifact pointers (not full content)

The harness must never use a hardcoded system prompt.

## 12) Minimal success criteria
- Machine can start a Mode from a user message and receive receipts.
- Mode emits artifact pointers and AHDB proposed deltas.
- Machine can promote a proposed AHDB delta only after a verifier receipt.
- Single-writer scheduling is enforced.

