# Context Graph Spec (v0): Cross-Run, Time-Sliced, Query-Conditioned Projections

This spec defines the **Context Graph**: a queryable, replayable projection over the machine’s event log and content-addressed object store.

Core idea:
- Truth is **EVENT LOG + OBJECT STORE** (content-addressed).
- A Context Graph is a **subgraph** selected by time interval and/or prompt-conditioned query.
- Context graphs can combine runs, compress into hierarchies (mind maps), and be narrated by a semantic layer.

---

## 0) Goals and non-goals

Goals
- Produce a graph view of “what happened” and “what matters” across multiple runs.
- Support time windows and prompt/query conditioning.
- Be replayable and auditable (content-addressed root + receipts).
- Support hierarchical compression for visualization.
- Support deterministic query execution plus semantic narration.

Non-goals (v0)
- Perfect minimality (bounded usefulness > optimality).
- Full distributed graph database requirements on day one.
- Full time-travel forking (stretch).

---

## 1) Canonical substrate

### 1.1 Object store (immutable, content-addressed)
Objects (examples):
- WorkItem, Run, Mood, Lease, Receipt, Artifact, Attestation
- AHDBDelta, Hyperthesis, Conjecture
- EvidenceCard, EvidenceSet
- CommitReceipt, WorktreeReceipt
- SpecChangeRequest, DoctrineChangeRequest

ID:
- object_id = hash(canonical_bytes)

### 1.2 Event log (append-only)
Events reference objects by hash and include minimal metadata.
Rule: events store pointers, not large payloads.

Event examples:
- RUN_STARTED, RUN_FINISHED
- MOOD_TRANSITION
- LEASE_GRANTED, LEASE_REVOKED
- VERIFIER_REQUESTED, ATTESTATION_EMITTED
- PATCH_PROPOSED, COMMIT_APPROVED, WORKTREE_DISCARDED
- NOTE_APPENDED (typed)
- PUBLISH_REQUESTED, PUBLISHED (later)
- PROMOTION_REQUESTED, PROMOTION_FINALIZED (later)

---

## 2) Graph model

### 2.1 Nodes
Nodes correspond to content-addressed objects.

Required node types (v0):
- RUN
- WORK_ITEM
- MOOD (state marker node or attribute)
- LEASE
- RECEIPT
- ARTIFACT
- ATTESTATION
- AHDB_DELTA
- HYPERTHESIS
- CONJECTURE
- COMMIT (CommitReceipt)
- NOTE (typed)

### 2.2 Edges
Edges are relations between nodes; edges may be stored as content-addressed edge objects or derived from events.

Minimum edges:
- PRODUCED_BY(obj, run)
- CONSUMED_BY(obj, run)
- DEPENDS_ON(work_item, work_item)
- CAUSED_BY(event_or_receipt, prior_event_or_receipt)
- REVISES(new_doc, old_doc)
- ATTESTS(attestation, target_object)
- GRANTS(lease, syscall_class)
- ALLOWED(lease, run)
- VERIFIED_BY(commit, attestation_set)
- UPDATES(ahdb_delta, ahdb_projection_version)
- BOUNDS(hyperthesis, conjecture_or_work_item)

---

## 3) Context Graph definition

A **Context Graph** is a subgraph:
CG = (N, E) where N ⊆ AllNodes and E ⊆ AllEdges induced by selection + expansion.

A Context Graph is content-addressable via:
- canonicalized selector parameters
- event log cursor range (start/end event IDs)
- optional merkle root over included node IDs

---

## 4) Selectors (how to produce a context graph)

### 4.1 Time window selector
TIME_SELECTOR:
- t_start, t_end
- optional filters: mood, syscall class, work item tags, run status

Selection:
- include RUN nodes intersecting [t_start, t_end]
- include all objects referenced by events in the window
- include causal parents up to depth D_parent (bounded)

Output: “what transpired” graph.

### 4.2 Prompt/query-conditioned selector
QUERY_SELECTOR:
- query_text (string)
- optional typed intent
- scope constraints: runs/work_items/moods/object_types/tags
- retrieval budgets: top_k, depth, max_nodes

Two-stage:
1) Candidate retrieval (vector search over typed objects such as AHDBDelta/Hyperthesis/Conjecture/Attestation/EvidenceCard metadata)
2) Graph expansion (bounded):
   - add attestations supporting relevant assertions
   - add receipts/artifacts referenced
   - add related runs/work items via causal/provenance edges

Output: “what matters for this query” graph.

### 4.3 Explicit run-set selector
RUN_SET_SELECTOR:
- run_ids: [RunId]
- include_siblings (same work item)
- include_verifiers (attestations and receipts)

Output: combined cross-run graph.

---

## 5) Combining runs

Combine runs by union + induced edges:
- N = union of nodes across selected runs
- E = induced edges among N

Common combine views:
- “overnight batch” (all runs in a window)
- “all runs for work item X”
- “all runs touching syscall class NET”
- “all runs producing attestations for spec S”

---

## 6) Hierarchical compression (mind map view)

A context graph can be rendered hierarchically by clustering nodes.

Default hierarchy:
ROOT
- WORK_ITEMS
  - RUNS
    - MOOD segments
    - LEASES
    - VERIFIERS/ATTESTATIONS
    - COMMITS / DISCARDS
- STATE
  - AHDB deltas
  - conjectures
  - hypertheses
- ARTIFACTS (collapsed by default)

Compression rules:
- collapse raw logs into ARTIFACT nodes (no expansion by default)
- collapse repeated failure signatures into one node + count
- collapse repeated verifier runs into one node + timeline

Required UI features:
- expand/collapse by node type
- time slider (event cursor replay)
- heat overlays (context footprint)
- invariant overlays (red flags)

---

## 7) Replay and time travel

v0:
- deterministic replay of projections by reprocessing events in order
- time slider moves the cursor and recomputes the context graph/projections

stretch:
- fork the event log at cursor C (new branch id)
- inject events and reflow forward
Requires explicit branch semantics and causal invalidation.

---

## 8) Semantic layer integration

A semantic layer may:
- describe a context graph in prose (derived artifact)
- answer NL queries by compiling: query_text → typed selector → deterministic execution

Rules:
- graph is truth; narration is derived
- narration cites node handles and receipts

---

## 9) Output formats

A Context Graph must be exportable as:
- JSON (nodes + edges + metadata)
- a “graph handle” (content-addressed id + selector params)
- optional derived renders (SVG/PNG) as artifacts

---

## 10) Minimal implementation checklist

1) Define node schemas for core objects and events.
2) Implement event-log cursor queries (time window).
3) Implement graph assembly (node set + induced edges).
4) Implement vector retrieval over typed objects (AHDBDelta/Conjecture/Hyperthesis/Attestation).
5) Implement bounded expansion rules.
6) Implement hierarchical renderer (mind map).
7) Implement narration helper as derived artifact generator.

---

## 11) Doctrine block (prompt-ready)

CONTEXT GRAPH = PROJECTION.
- EVENT LOG + OBJECT STORE IS TRUTH.
- CONTEXT IS A SUBGRAPH SELECTED BY TIME OR QUERY.
- RAW ARTIFACTS STAY OUT-OF-BAND.
- EVERYTHING IS CONTENT-ADDRESSED AND REPLAYABLE.
