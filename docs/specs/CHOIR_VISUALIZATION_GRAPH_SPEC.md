# Choir Visualization Graph Spec (v0)
Status: DRAFT
Date: 2026-01-23
Owner: ChoirOS Core

## Decision summary
The UI visualization is a graph of runs, modes, receipts, artifacts, and AHDB deltas. It is built from the event log (NATS) or SQLite projection and supports live processing and replay.

## Goals
- Show why a decision happened (traceable receipts + artifacts).
- Support live mode execution visualization.
- Support replay from event log.

## Non-goals (v0)
- Global social graph.
- Complex 3D layouts.

## Node types
- Run
- Mode
- Work item
- Receipt
- Artifact
- AHDB delta (asserted vs proposed)

## Edge types
- run->mode (execution)
- run->receipt (emitted)
- receipt->artifact (evidence)
- artifact->ahdb_delta (support)
- work_item->run (scheduled)

## Data sources
- Primary: NATS event stream.
- Secondary: SQLite projection (for replay and offline).

## UI behaviors
- Live stream mode: append nodes as events arrive.
- Replay mode: rebuild from a selected sequence range.
- Expand/collapse: show artifacts and receipts only when focused.

## Event mapping
- mode.start / mode.stop / mode.update -> Mode node + edges
- receipt.* -> Receipt node
- artifact.create / artifact.pointer -> Artifact node
- receipt.ahdb.delta -> AHDB delta node

## Success criteria
- User can trace an AHDB delta to artifacts and receipts.
- Live updates render without blocking interaction.
- Replay produces same graph as live stream.
