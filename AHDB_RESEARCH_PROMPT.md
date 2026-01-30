# AHDB Architecture Research Agenda

**Status**: Active Research Project
**Methodology**: PREDICTION → EXPERIMENT → OBSERVE
**Updated**: 2026-01-27

---

## Executive Summary

This document outlines an **automated research project** to discover the correct architecture for ChoirOS through systematic experimentation.

**Core Insight**: AHDB is not a database. It's **context engineering** - the assembly and framing of information that gets passed to each worker agent in their system message.

**Research Questions**:
1. What role do queues play in the system?
2. Are we using NATS correctly?
3. What are "modes" really - capabilities, risk levels, or something else?
4. How should AHDB be assembled into worker context?
5. What's the relationship between AHDB and the Context Map?

**Method**: For each question, we form a hypothesis, design a minimal experiment, and observe what breaks or works.

---

## The Architecture (As Understood)

### Current Event Flow

```
Input (email/command/app)
  ↓
[First Event]
  ↓
Deterministic Processing
  ↓
Context Engineering (Supervisor)
  ↓
Decision: Direct Response OR Directive to Modes?
  ↓
[If Simple] → Direct response ("hi" → "hello!")
[If Complex] → Directive → One or more Modes execute
  ↓
Modes (as their own agents) emit events
  ↓
Supervisor subscribes to mode events
  ↓
Observability & Learning
```

### Key Components

**AHDB (Agent Hypothesis Database)**:
- Originally: Assert, Hypothesis, Drive, Believe (a cognitive pattern)
- Current: Key-value store in SQLite
- Actual: Should be **context assembly** - gathering sources, ranking relevance, injecting into system message

**Supervisor**:
- Receives inputs
- Does context engineering
- Decides: handle directly or delegate to modes?
- Subscribes to mode events for observability

**Modes**:
- CALM, CURIOUS, SKEPTICAL, PARANOID, BOLD, CONTRITE
- Question: Are these "capability categories" or something else?

**NATS**:
- Currently: Pub/sub for events
- Question: Should it also be work queues?

**Missing**: Queues between input and supervisor?

---

## Research Questions & Experiments

### Question 1: Do We Need Queues?

**Context**: Current system has everyone subscribing to everything. No buffering between inputs and processing.

**Hypothesis**: Adding a work queue between "input received" and "supervisor processing" will:
- Increase throughput by 3x during burst load
- Prevent dropped events during spikes
- Allow multiple workers to process in parallel

**Experiment**:
1. Create JetStream pull consumer: `choiros.inputs.user.{user_id}`
2. Route all inputs to this queue instead of direct pub/sub
3. Spin up 5 supervisor workers
4. Send 1000 inputs as fast as possible
5. Measure: processing time, dropped events, worker idle time, queue depth

**Observe**:
- If confirmed: 3x throughput, workers stay busy, zero drops
- If refuted: No improvement, or workers block waiting, or events get stuck
- If inconclusive: Need different queue configuration

**Files to Modify**:
- `supervisor/machine.py` - add queue consumer
- `api/routers/parse.py` - publish to queue instead of direct
- Test: `supervisor/tests/test_queue_experiment.py`

**Duration**: 2-3 hours to implement and run

---

### Question 2: Are We Using NATS Correctly?

**Context**: We're using NATS as pure pub/sub. Everything subscribes to everything. No separation of concerns.

**Hypothesis**: We should separate:
- **Input queue** (pull consumer): Work to be processed
- **Observability stream** (push consumer): Events for UI/dashboard
- **Mode event streams** (push): Inter-mode communication

**Experiment**:
1. Create separate streams:
   - `INPUTS` (pull, work queue)
   - `OBSERVABILITY` (push, UI events)
   - `MODE_EVENTS` (push, mode coordination)
2. Route events to appropriate stream based on type
3. Measure: Separation of concerns, ability to scale independently, complexity

**Observe**:
- If confirmed: Clean separation, can scale input workers independently from UI consumers
- If refuted: Too complex, routing logic is nightmare, no benefit
- If inconclusive: Partial separation works (e.g., inputs vs observability)

**Files to Modify**:
- `supervisor/event_contract.py` - add stream routing logic
- `supervisor/db.py` - separate stream creation
- Configuration: Docker NATS config

**Duration**: 3-4 hours

---

### Question 3: What Are "Modes" Really?

**Context**: We have CALM, CURIOUS, SKEPTICAL, PARANOID, BOLD, CONTRITE. Are these "capability categories" or something else?

**Competing Hypotheses**:

**Hypothesis A**: Modes are *risk levels*
- CALM = low risk, low verification
- SKEPTICAL = medium risk, medium verification
- PARANOID = high risk, high verification
- Prediction: Each mode should have a (risk_tolerance, verification_cost) tuple

**Hypothesis B**: Modes are *verification strategies*
- CALM = test once, assume it works
- SKEPTICAL = test three ways before believing
- PARANOID = adversarial testing, try to break it
- Prediction: Each mode should have a testing_strategy

**Hypothesis C**: Modes are *capability categories*
- CALM = can do file reads
- PARANOID = can do file writes
- BOLD = can do network operations
- Prediction: Each mode has a capability_allowlist

**Experiment**:
1. Review `supervisor/mode_engine.py` - current mode definitions
2. For each mode, extract:
   - What tools it allows
   - What verification it requires
   - What triggers it
3. Cluster modes by these properties
4. See which hypothesis fits the clustering

**Observe**:
- If A fits: Modes cluster by risk level
- If B fits: Modes cluster by verification strategy
- If C fits: Modes cluster by capability
- If none fit: Modes are something else entirely

**Files to Analyze**:
- `supervisor/mode_engine.py`
- `supervisor/machine.py` (mode selection logic)
- Test: `supervisor/tests/test_mode_clustering.py`

**Duration**: 2 hours (analysis only)

---

### Question 4: How Should AHDB Be Assembled?

**Context**: AHDB currently lives in SQLite as key-value pairs. But it's supposed to be "context engineering" for worker system messages.

**Hypothesis**: AHDB is a *prompt assembly problem*:
- Multiple sources: recent events, assertions, hypotheses, user history, mode constraints
- Limited context window: LLMs can only take ~128k tokens
- Need ranking: What's most relevant for this specific task?
- Need formatting: How to structure for maximum LLM understanding?

**Experiment**:
1. Build a prototype `ContextBuilder` that:
   - Takes: task description, user_id, mode
   - Gathers: recent events (last 50), AHDB assertions, user history, mode constraints
   - Ranks by: relevance score (TF-IDF or embedding similarity)
   - Formats: structured sections for LLM
2. Generate context for 10 sample tasks
3. Measure: Context size, relevance scores (human judgment), LLM performance

**Observe**:
- If confirmed: LLMs make better decisions with ranked context
- If refuted: Context assembly doesn't help, or ranking is wrong
- If inconclusive: Need better ranking algorithm

**Files to Create**:
- `supervisor/context_builder.py` (new)
- Test: `supervisor/tests/test_context_assembly.py`

**Duration**: 4-5 hours

---

### Question 5: AHDB vs Context Map - What's the Relationship?

**Context**: We have two visualizations:
- AHDB: "Agent Hypothesis Database" (conceptual)
- Context Map: Visual graph of relationships

**Hypothesis**: These are the same thing, just different representations:
- AHDB = the underlying data (assertions, hypotheses, beliefs)
- Context Map = visual graph of that data
- Prediction: If we update AHDB, the Context Map should auto-update

**Alternative Hypothesis**: They serve different purposes:
- AHDB = internal context for agents (system message)
- Context Map = external visualization for humans (UI)
- Prediction: They have different data schemas and update frequencies

**Experiment**:
1. Define schema for both AHDB and Context Map
2. Build a sync mechanism: AHDB changes → Context Map updates
3. Test: Add assertion to AHDB, check if Context Map updates
4. Test: Remove assertion, check update
5. Test: Add hypothesis, check if it appears differently from assertion

**Observe**:
- If hypothesis confirmed: One-way sync works, they're views of same data
- If refuted: Schemas are incompatible, they're fundamentally different
- If inconclusive: Partial overlap, need transformation layer

**Files to Analyze/Create**:
- `supervisor/db.py` (AHDB schema)
- `choiros/src/components/apps/ContextMindMap.tsx` (Context Map component)
- New: `supervisor/context_map_sync.py`?

**Duration**: 3-4 hours

---

## Research Log

### Experiment Log Template

```markdown
## [Experiment Name]

**Date**: YYYY-MM-DD
**Researcher**: [Agent/Human]
**Question**: Which research question does this address?

### PREDICTION
[Hypothesis: what do you think will happen?]

### EXPERIMENT
[Steps taken]

### OBSERVE
[Results: what actually happened?]

### LEARNING
- Hypothesis: [Confirmed / Refuted / Inconclusive]
- What did we learn?
- What's the next experiment?
```

---

### Completed Experiments

- 2026-01-29T01:33:03.200236Z | q1-queue-throughput | supported | JetStream pull consumers show multi-worker throughput lift on queue workloads.
- 2026-01-29T01:33:03.217516Z | q2-stream-separation | supported | JetStream stream separation test confirms isolated subjects per stream.
- 2026-01-29T01:33:03.219008Z | q3-modes-classification | supported | Mode selection responds to risk/verification signals, while mode configs enforce capability boundaries (write/network/tooling).
- 2026-01-29T01:33:03.220775Z | q4-context-assembly | supported | Ranking reduces context size and retrieves expected keys for most tasks, but LLM performance remains untested.
- 2026-01-29T01:33:03.232863Z | q5-ahdb-vs-context-map | supported | AHDB deltas do not appear in context heatmap nodes, suggesting separate data shapes.

---

## Next Actions (For Automated Research Agent)

When you start this research project:

1. **Run the automated research runner**:
   - `python -m supervisor.research.runner run`
   - Logs: `docs/research/experiment_runs.jsonl`
   - Per-run notes: `docs/research/runs/`

2. **Review results**:
   - Completed experiments are auto-updated in this file
   - Use the logs to decide which hypothesis to pursue next

3. **If an experiment requires code changes**:
   - Create a branch: `git checkout -b research/question-N-experiment-name`
   - Implement the experiment as a runnable module in `supervisor/research/experiments.py`
   - Re-run the automated runner to record results

4. **Proceed to the next experiment** based on learning

---

## Success Criteria

**Research is successful when**:
- We have clear answers to all 5 questions
- Architecture is documented and testable
- Each hypothesis is confirmed/refuted with evidence
- We have a working prototype that demonstrates the architecture

**Signs we're on the right track**:
- Experiments produce clear results (not "it depends")
- Findings inform next experiments (each builds on previous)
- Architecture simplifies, not complicates
- We can explain it in one paragraph

**Signs we're going in circles**:
- Same experiments repeated with different parameters
- Findings don't inform next steps
- Architecture keeps getting more complex
- "It depends" on everything

---

## Appendix: Related Documents

- `CLAUDE.md` - Development guidelines (including P/E/O protocol)
- `AGENTS.md` - Agent development patterns
- `docs/specs/AHDB_HYPOTHESIS_PROTOCOL_REDESIGN.md` - Previous redesign attempt (too ambitious)
- `docs/specs/CHOIR_MACHINE_V0_SPEC.md` - Machine architecture
- `docs/specs/CHOIR_MOODS_SPEC.md` - Mode specifications
- `docs/doctrine/THE_MIND_MODEL.md` - Philosophy behind AHDB

---

## Philosophy

This is not a 12-week plan. This is a **scientific discovery process**.

We don't argue about architecture. We:
1. Form a hypothesis
2. Build the minimum thing to test it
3. Observe what breaks
4. Learn from the evidence
5. Revise our understanding

Each experiment should take **hours, not days**. Each should produce a **clear learning**. The architecture will **emerge** from the evidence, not from planning.

**The goal**: Not to "build the right architecture," but to **discover it through experimentation**.

That's the AHDB pattern applied to architecture itself.
