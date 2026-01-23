# Choir Auditor Multipass Spec (v0)
Status: DRAFT
Date: 2026-01-23
Owner: ChoirOS Core

## Decision summary
Auditing is a worker Mode. The Machine does not perform research. The auditor runs a multipass loop inside a sandboxed Mode: retrieve → critique → refine → citations. Output is artifacts + receipts, not free-form prose.

## Goals
- Long-running audit loop with retrieval and citations.
- Clear separation between Machine (outer) and auditor Mode (inner).
- Evidence is stored as artifacts; outputs are pointer-based.
- Emits structured receipts and AHDB proposals (not assertions).

## Non-goals (v0)
- Automatic promotion of assertions.
- Multi-tenant or crowd-sourced audit.

## Inputs
- Target: URL or file path.
- Lens: purpose/criteria (security, correctness, bias, etc.).
- Budgets: max sources, tokens, passes.

## Loop phases
1) Retrieve
- Use allowlisted retrieval tools.
- Store raw evidence as artifacts.
- Emit artifact.pointer for each evidence set.

2) Critique
- Analyze evidence, generate critique and blind spots.
- Emit structured critique artifact + receipt.context.footprint.

3) Refine
- Run a second pass based on blind spots.
- Produce updated critique and citations.

4) Emit
- Emit citations as pointers to artifacts.
- Emit AHDB proposed deltas (authority=proposed).

## Outputs
- artifact.create / artifact.pointer for evidence, critique, and logs.
- receipt.retrieval
- receipt.context.footprint
- receipt.ahdb.delta (authority=proposed)

## Safety rules
- No assertion without verifier receipts.
- No raw source content in the Machine context.
- All evidence references are pointer-based.

## Success criteria
- Auditor produces citations and artifacts for each pass.
- Machine receives only pointers and summaries, not raw sources.
- Audit runs are reproducible via artifacts + receipts.
