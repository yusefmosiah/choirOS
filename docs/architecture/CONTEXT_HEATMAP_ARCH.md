# Context Heatmap Mind Map Architecture
Status: Draft
Owner: ChoirOS Core
Updated: 2026-01-23

## Goals
- Provide a live, low-latency mind map of active context across runs, tools, files, and receipts.
- Support replay by recomputing the mind map from a chosen event sequence.
- Keep the visualization deterministic and cheap by deriving from the event log projection.

## Non-goals
- Perfect semantic clustering or NLP summarization.
- 3D or force-directed simulation.
- Cross-user multi-tenant views (handled by auth scope).

## System overview
The context heatmap is a thin projection over the event log. The supervisor exposes a read model that aggregates events into nodes (entities like files, tools, messages) and edges (context links). The frontend renders the snapshot as a radial mind map with heat-weighted opacity and a replay slider that requests earlier snapshots.

```
NATS / SQLite Event Log
        │
        ▼
Supervisor EventStore.build_context_heatmap
        │
        ▼
GET /observability/context-heatmap
        │
        ▼
Context Heatmap App (mind map + replay)
```

## Data model
### Node
- `id` (string): stable identity like `file:docs/spec.md`
- `label` (string): display label
- `type` (string): `file`, `tool`, `message`, `conversation`, `run`, `receipt`, `note`, `artifact`, `event`, `root`
- `heat` (float): normalized score from recency-decayed event counts
- `event_count` (int): number of events contributing to the node
- `last_seq` (int): most recent event sequence for the node
- `last_timestamp` (string | null)
- `metadata` (object): optional metadata used in UI

### Edge
- `source` (string): node id
- `target` (string): node id
- `type` (string): `context`, `invokes`, `message`
- `weight` (float): aggregated strength of the relationship

## Heat scoring
- Each event contributes `exp(-age / 40)` to its node score (age = latest_seq - event_seq).
- Scores are normalized by the max score in the snapshot to produce `heat` in `[0, 1]`.

## Replay workflow
1. UI requests `/observability/context-heatmap?until_seq=<cursor>` when the replay slider moves.
2. Supervisor loads events `seq > since_seq` and `seq <= until_seq`, rebuilds the snapshot, and returns it.
3. UI renders the snapshot without polling in replay mode.

## Live workflow
1. UI polls `/observability/context-heatmap` every 4 seconds.
2. Supervisor responds with the latest snapshot and `latest_seq`.
3. UI updates node opacity and layout without reloading the app.

## Failure modes & mitigations
- **Large logs**: limit query window (`limit` parameter) and clamp in API (1–2000).
- **Missing payloads**: use default labels and metadata fallback.
- **NATS offline**: SQLite projection still produces snapshots, enabling replay.

## Extensibility
- Add projection-specific edges (e.g., file -> tool for tool.write) by enriching event payloads.
- Emit `receipt.context.footprint` nodes once receipts include footprints.
- Add clustering or grouping in UI by type or path prefix.
