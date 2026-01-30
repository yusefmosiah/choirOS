# AHDB Hypothesis Protocol Redesign
**Making PREDICTION/EXPERIMENT/OBSERVE the Foundational Primitive**

Status: PROPOSAL
Date: 2026-01-27
Author: ChoirOS Core Team

---

## Executive Summary

**Current State**: ChoirOS has all the components for scientific experimentation (AHDB, Modes, Verifiers, Events), but they operate as separate mechanisms. The Machine treats work items as tasks to complete, not hypotheses to test.

**Proposed State**: PREDICTION/EXPERIMENT/OBSERVE becomes the primitive operation of the entire system. Every agent action is a hypothesis test. AHDB is not just a "database" - it's the accumulated learning from thousands of experiments.

**Key Insight**: When PREDICTION/EXPERIMENT/OBSERVE is the foundation:
- Agents don't "do work" - they run experiments
- Features aren't "built" - they're hypothesized and verified
- Knowledge isn't "stored" - it's accumulated evidence
- Development isn't "coding" - it's scientific inquiry

---

## Phase 1: Audit - Current State Analysis

### 1.1 Architecture Audit

#### Machine: Task Runner, Not Experiment Engine
**File**: `/Users/wiz/choirOS/supervisor/machine.py`

**Current Behavior**:
```python
# Line 108-143: The scheduler loop
item = self.store.claim_next_work_item(runner_id)
# ...
mode_config = self._select_mode(prompt)
# ...
await self._run_directive(directive, emit_start=True)
```

**Problem**:
- Work items are treated as opaque tasks
- No hypothesis tracking before execution
- No explicit prediction about what will happen
- No structured observation of results
- Mode selection is based on AHDB state, but AHDB updates are事后 (after-the-fact)

**What's Missing**:
1. Hypothesis formation step before mode selection
2. Expected outcomes declared upfront
3. Discriminating tests identified in advance
4. Observation structure (what did we learn?)
5. Confidence tracking in predictions

#### Mode Engine: Capability Gating, Not Hypothesis Spaces
**File**: `/Users/wiz/choirOS/supervisor/mode_engine.py`

**Current Behavior**:
```python
@dataclass(frozen=True)
class ModeInputs:
    crash_detected: bool = False
    has_demo: bool = True
    # ... 16 boolean flags
```

**Problem**:
- Modes are configured by boolean flags
- No representation of what hypothesis the Mode is testing
- No explicit connection between Mode purpose and experimental outcome
- Transitions are reactive (something failed → switch mode), not experimental (hypothesis refuted → new hypothesis)

**What's Missing**:
1. Modes as "hypothesis spaces" with different prediction strategies
2. Each Mode declares what it's trying to learn
3. Mode transitions are hypothesis revisions, not just error handling
4. CALM doesn't mean "safe execution" - it means "test this specific prediction with low risk"

#### AHDB: State Vector, Not Hypothesis Database
**File**: `/Users/wiz/choirOS/supervisor/db.py` (lines 112-125)

**Current Schema**:
```python
CREATE TABLE IF NOT EXISTS ahdb_state (
    key TEXT PRIMARY KEY,
    value JSON NOT NULL,
    updated_at TEXT NOT NULL
);
```

**Problem**:
- AHDB is a key-value store, not a hypothesis registry
- No tracking of predicted vs observed outcomes
- No confidence or evidence weight
- No lineage: which hypotheses led to which assertions?
- "HYPOTHESIZE" is just a key, not a first-class object

**What's Missing**:
1. Hypothesis registry table (id, prediction, experiment, observation)
2. Evidence chain linking predictions to outcomes
3. Confidence scoring and calibration tracking
4. Hypothesis dependency graph (A depends on B)
5. Refutation tracking (what we learned from failures)

#### Event Contract: Events Exist, No Hypothesis Lifecycle
**File**: `/Users/wiz/choirOS/supervisor/event_contract.py`

**Current Event Types**:
```python
"note.hypothesis",
"note.hyperthesis",
"note.conjecture",
"receipt.ahdb.delta",
```

**Problem**:
- `note.hypothesis` is just a note type, not a lifecycle
- No `hypothesis.created` → `hypothesis.running` → `hypothesis.confirmed/refuted` flow
- No link between predictions and observations
- No way to trace: "I thought X would happen, I did Y, and Z occurred"

**What's Missing**:
1. First-class hypothesis events (not notes)
2. Hypothesis lifecycle state machine
3. Discriminating test events
4. Prediction vs observation comparison events

### 1.2 Agent Development Audit

#### Agent Harness: Tool Executor, Not Experiment Runner
**File**: `/Users/wiz/choirOS/supervisor/agent/harness.py`

**Current Loop** (lines 113-241):
```python
while True:
    final_plan = await stream.get_final_response()

    if final_plan.final_response:
        break

    for tc in final_plan.tool_calls:
        result = await self.tools.execute_tool(tc.tool_name, tc.tool_args)
        # Log result
```

**Problem**:
- Agent calls tools without declaring predictions
- No hypothesis: "I expect this tool to return X"
- No discriminating test: "If Y happens, my hypothesis is wrong"
- Tool results are just data, not evidence for/against beliefs

**What's Missing**:
1. Every tool call wrapped in a hypothesis context
2. Agent must predict tool outcome before execution
3. Unexpected tool results trigger hypothesis revision
4. Evidence accumulation, not just task completion

#### BAML Integration: Unstructured Plans, Not Testable Hypotheses
**Directory**: `/Users/wiz/choirOS/supervisor/baml_client/`

**Current State**:
- BAML defines `PlanAction` (thinking + tool_calls)
- No structured prediction format
- No confidence scoring
- No discriminating tests

**What's Missing**:
1. `FormHypothesis` BAML function (returns prediction + discriminating test)
2. `ObserveOutcome` BAML function (updates belief based on evidence)
3. Confidence tracking in BAML schemas
4. Hypothesis revision prompts

### 1.3 Testing Audit

#### Current Testing Pattern: Separate, Not Embedded
**Finding**: Tests are separate files (`test_*.py`), not integrated into features

**Problem**:
- Tests verify code after it's written
- No prediction before implementation
- Tests don't track hypotheses over time
- No evidence accumulation from test runs

**What's Missing**:
1. Every feature starts with a testable hypothesis
2. Tests are predictions, not after-the-fact verification
3. Test results feed into AHDB as evidence
4. "PREDICTION → EXPERIMENT → OBSERVE" in test structure

### 1.4 Documentation Audit

#### CLAUDE.md: Mentions P/E/O, Doesn't Operationalize It
**File**: `/Users/wiz/choirOS/CLAUDE.md` (line 127)

**Current State**:
```markdown
7. **Testing Discipline**: Every feature or fix must include automated tests
   and explicit PREDICTION → EXPERIMENT → OBSERVE criteria.
```

**Problem**:
- P/E/O is mentioned as a testing principle, not a system primitive
- No guidance on how to write predictions
- No structure for experiments
- No observation format

**What's Missing**:
1. P/E/O template for every agent action
2. Hypothesis declaration format
3. Observation logging format
4. Confidence tracking guidelines

---

## Phase 2: Redesign - Making P/E/O the Foundation

### 2.1 Core Data Structures

#### Hypothesis (First-Class Object)
```python
@dataclass
class Hypothesis:
    id: str  # UUID
    agent_id: str  # Which agent formed this
    run_id: str  # Which execution run

    # PREDICTION
    prediction: str  # Natural language: "I believe X will happen"
    predicted_outcome: Dict[str, Any]  # Structured prediction
    confidence: float  # 0.0-1.0, how sure am I?
    discriminating_test: str  # "If Y happens, I'm wrong"

    # EXPERIMENT
    experiment_type: str  # "tool_call", "verification", "mode_transition"
    experiment_config: Dict[str, Any]  # What we'll do
    required_verifiers: List[str]  # How we'll measure success

    # OBSERVATION (filled after execution)
    observed_outcome: Optional[Dict[str, Any]] = None
    actual_result: Optional[Dict[str, Any]] = None
    verifier_results: Optional[List[Dict]] = None

    # LEARNING
    status: Literal["pending", "running", "confirmed", "refuted", "inconclusive"]
    confidence_after: Optional[float] = None  # Updated confidence
    learning_summary: Optional[str] = None  # What did we learn?
    evidence_artifacts: List[str] = field(default_factory=list)  # Artifact hashes

    # METADATA
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: Optional[str] = None
    parent_hypothesis_id: Optional[str] = None  # For chaining
```

#### Experiment (Executable Unit)
```python
@dataclass
class Experiment:
    id: str
    hypothesis_id: str  # Links to Hypothesis

    # What we're doing
    mode: str  # CALM, CURIOUS, etc.
    tool_calls: List[ToolCall]
    budget: Budget

    # What we're measuring
    metrics: List[str]  # ["return_code", "execution_time", "test_pass_rate"]
    artifact_paths: List[str]  # What to capture

    # Execution state
    status: Literal["pending", "running", "completed", "failed"]
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
```

#### Observation (Evidence Record)
```python
@dataclass
class Observation:
    id: str
    experiment_id: str
    hypothesis_id: str

    # What happened
    actual_outcome: Dict[str, Any]
    unexpected_events: List[str]
    metrics: Dict[str, float]

    # Evidence
    artifact_hashes: List[str]
    verifier_attestations: List[Dict]

    # Comparison
    prediction_match: bool  # Did it match the hypothesis?
    discrepancy_magnitude: float  # How wrong were we?

    # Learning
    surprise_level: float  # 0.0 (expected) to 1.0 (shocking)
    suggests_revision: bool  # Should we update our beliefs?

    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
```

### 2.2 New Event Types

```python
# Hypothesis lifecycle events
"hypothesis.created",      # Agent forms a hypothesis
"hypothesis.running",       # Experiment starts
"hypothesis.completed",     # Experiment finished
"hypothesis.confirmed",     # Prediction was correct
"hypothesis.refuted",       # Prediction was wrong
"hypothesis.inconclusive",  # Couldn't determine

# Experiment events
"experiment.started",       # Experiment execution begins
"experiment.metric",        # Metric observation
"experiment.artifact",      # Artifact captured
"experiment.failed",        # Experiment crashed

# Observation events
"observation.logged",       # Raw observation recorded
"prediction.compared",      # Prediction vs observation
"learning.extracted",       # What we learned
```

### 2.3 Redesigned Agent Loop

**Current Loop (Task-Oriented)**:
```python
while has_work():
    action = select_action()
    result = execute(action)
    if result.is_complete():
        break
```

**New Loop (Hypothesis-Oriented)**:
```python
while has_unanswered_questions():
    # PREDICTION
    hypothesis = await form_hypothesis(context, evidence_so_far)
    store.append("hypothesis.created", hypothesis.to_dict())

    # EXPERIMENT
    experiment = design_experiment(hypothesis)
    store.append("experiment.started", experiment.to_dict())

    observation = await run_experiment(experiment)
    store.append("observation.logged", observation.to_dict())

    # OBSERVE
    learning = compare_prediction_to_observation(hypothesis, observation)

    if learning.is_confirmed():
        store.append("hypothesis.confirmed", learning.to_dict())
        update_ahdb(assertions=learning.extract_assertions())
    elif learning.is_refuted():
        store.append("hypothesis.refuted", learning.to_dict())
        update_ahdb(beliefs=learning.revise_beliefs())
    else:
        store.append("hypothesis.inconclusive", learning.to_dict())
        # Form new hypothesis with refined discriminating test

    # Calibration: Track how well our predictions match reality
    calibrate_confidence(hypothesis, observation)
```

### 2.4 Redesigned Machine

**Current Machine**: Mode Orchestrator
```python
class Machine:
    def _scheduler_loop(self):
        item = self.store.claim_next_work_item()
        mode = self._select_mode(item.description)
        await self._run_directive(mode, item)
```

**New Machine**: Hypothesis Engine
```python
class HypothesisMachine:
    def _experiment_loop(self):
        # Get pending hypotheses (not work items)
        hypothesis = self.store.claim_next_hypothesis()

        # Design experiment based on hypothesis
        experiment = self._design_experiment(hypothesis)

        # Select mode based on hypothesis risk and confidence
        mode = self._select_mode_for_experiment(hypothesis, experiment)

        # Run experiment as hypothesis test
        observation = await self._run_experiment(mode, experiment)

        # Update AHDB based on what we learned
        self._integrate_observation(hypothesis, observation)
```

**Key Changes**:
1. Work queue becomes hypothesis queue
2. Mode selection considers hypothesis confidence
3. Execution produces observations, not just results
4. AHDB updates are evidence-weighted, not binary

### 2.5 Redesigned AHDB Schema

**Current Schema**:
```sql
CREATE TABLE ahdb_state (
    key TEXT PRIMARY KEY,
    value JSON NOT NULL,
    updated_at TEXT NOT NULL
);
```

**New Schema**:
```sql
-- Hypothesis registry
CREATE TABLE hypotheses (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    run_id TEXT NOT NULL,

    -- Prediction
    prediction TEXT NOT NULL,
    predicted_outcome JSON NOT NULL,
    confidence REAL NOT NULL,
    discriminating_test TEXT NOT NULL,

    -- Experiment
    experiment_type TEXT NOT NULL,
    experiment_config JSON NOT NULL,
    required_verifiers JSON NOT NULL,

    -- Observation
    observed_outcome JSON,
    actual_result JSON,
    verifier_results JSON,

    -- Learning
    status TEXT NOT NULL,
    confidence_after REAL,
    learning_summary TEXT,
    evidence_artifacts JSON,

    -- Lineage
    parent_hypothesis_id TEXT,
    created_at TEXT NOT NULL,
    finished_at TEXT,

    FOREIGN KEY (parent_hypothesis_id) REFERENCES hypotheses(id)
);

-- Evidence chain
CREATE TABLE hypothesis_evidence (
    id TEXT PRIMARY KEY,
    hypothesis_id TEXT NOT NULL,
    evidence_type TEXT NOT NULL,  -- "prediction", "observation", "verification"
    artifact_hash TEXT NOT NULL,
    strength REAL NOT NULL,  -- How strong is this evidence?
    created_at TEXT NOT NULL,

    FOREIGN KEY (hypothesis_id) REFERENCES hypotheses(id)
);

-- Confidence calibration
CREATE TABLE confidence_tracking (
    id TEXT PRIMARY KEY,
    hypothesis_id TEXT NOT NULL,
    predicted_confidence REAL NOT NULL,
    actual_accuracy REAL NOT NULL,  -- 0.0 = wrong, 1.0 = correct
    surprise_level REAL NOT NULL,
    created_at TEXT NOT NULL,

    FOREIGN KEY (hypothesis_id) REFERENCES hypotheses(id)
);

-- AHDB as materialized view from hypotheses
CREATE VIEW ahdb_asserted AS
SELECT key, value, MAX(created_at) as updated_at
FROM hypotheses
WHERE status = 'confirmed'
AND confidence_after > 0.9
GROUP BY key, value;

CREATE VIEW ahdb_hypothetical AS
SELECT key, value, AVG(confidence) as avg_confidence, COUNT(*) as evidence_count
FROM hypotheses
WHERE status IN ('pending', 'running')
GROUP BY key, value;
```

### 2.6 BAML Integration

**New BAML Functions**:

```baml
// Form a hypothesis before taking action
function FormHypothesis(
    context: Context,
    evidence: Evidence[],
    proposed_action: Action
) -> Hypothesis {
    // What do I predict will happen?
    prediction: string

    // Structured prediction (e.g., file will exist, test will pass)
    predicted_outcome: PredictedOutcome

    // How sure am I? (0.0 to 1.0)
    confidence: float

    // What would prove me wrong?
    discriminating_test: string

    // What evidence supports this?
    supporting_evidence: Evidence[]
}

// Learn from observation
function ExtractLearning(
    hypothesis: Hypothesis,
    observation: Observation
) -> Learning {
    // Was I right?
    confirmed: boolean

    // What did I actually learn?
    learning_summary: string

    // How should I update my beliefs?
    belief_updates: BeliefDelta[]

    // What should I assert to AHDB?
    assertions_to_promote: Assertion[]

    // What new questions do I have?
    new_hypotheses_to_form: HypothesisPrompt[]
}

// Revise hypothesis after refutation
function ReviseHypothesis(
    refuted_hypothesis: Hypothesis,
    observation: Observation
) -> Hypothesis {
    // Why was I wrong?
    failure_analysis: string

    // What's the new hypothesis?
    revised_prediction: string

    // What's a better discriminating test?
    refined_discriminating_test: string

    // Increased or decreased confidence?
    new_confidence: float
}
```

---

## Phase 3: Implementation Strategy

### 3.1 Migration Path (Incremental)

#### Phase 1: Add Hypothesis Tracking (Minimal Change)
**Goal**: Start tracking hypotheses without changing execution flow

**Changes**:
1. Add `hypotheses` table to AHDB
2. Add `hypothesis.created` event when agent starts work
3. Add `hypothesis.completed` event when work finishes
4. Log predictions and observations as notes

**Risk**: Low - additive only, doesn't break existing flow

**Example**:
```python
# In agent harness, before tool call:
hypothesis = {
    "prediction": "Reading this file will return the function signature",
    "confidence": 0.9,
    "discriminating_test": "If file is missing, hypothesis is refuted"
}
store.append("hypothesis.created", hypothesis)

# After tool call:
observation = {
    "actual_outcome": tool_result,
    "prediction_match": True
}
store.append("hypothesis.completed", observation)
```

#### Phase 2: Integrate Hypotheses into Mode Selection
**Goal**: Make mode selection hypothesis-aware

**Changes**:
1. Machine reads pending hypotheses before selecting mode
2. Mode config includes `acceptable_hypothesis_confidence_range`
3. Low confidence hypotheses → CURIOUS mode
4. High confidence hypotheses → CALM mode
5. Refuted hypotheses → SKEPTICAL mode

**Risk**: Medium - changes mode selection logic

**Example**:
```python
def _select_mode(self, hypothesis: Hypothesis) -> ModeConfig:
    if hypothesis.confidence < 0.5:
        return get_mode_config("CURIOUS")  # Need more evidence
    elif hypothesis.status == "refuted":
        return get_mode_config("SKEPTICAL")  # Verify assumptions
    else:
        return get_mode_config("CALM")  # Test the prediction
```

#### Phase 3: Redesign Agent Loop
**Goal**: Make agent explicitly predict before acting

**Changes**:
1. BAML `FormHypothesis` called before `PlanAction`
2. Agent cannot call tools without a hypothesis
3. Unexpected tool results trigger hypothesis revision
4. Confidence calibration after every observation

**Risk**: High - changes core agent loop

**Example**:
```python
# New agent loop:
hypothesis = await b.FormHypothesis(context, proposed_action)
store.append("hypothesis.created", hypothesis.to_dict())

plan = await b.PlanAction(context, hypothesis)

for tool_call in plan.tool_calls:
    result = await execute_tool(tool_call)

    observation = compare_to_prediction(hypothesis, result)
    if observation.surprise_level > 0.7:
        # Something unexpected happened - revise hypothesis
        revised = await b.ReviseHypothesis(hypothesis, observation)
        store.append("hypothesis.revised", revised.to_dict())
```

#### Phase 4: Full Hypothesis-Driven Machine
**Goal**: Work queue becomes hypothesis queue

**Changes**:
1. `work_items` table deprecated, replaced by `hypotheses`
2. Machine prioritizes hypotheses by information gain
3. AHDB is materialized view from confirmed hypotheses
4. Every system action is a hypothesis test

**Risk**: High - architectural change

**Example**:
```python
# Old:
work_item = store.claim_next_work_item()

# New:
hypothesis = store.claim_next_hypothesis(
    order_by="information_gain DESC"
)
```

### 3.2 First Steps (Highest Value, Lowest Risk)

**Step 1: Add Hypothesis Logging (Week 1)**
- Add `hypotheses` table
- Log predictions in `agent/harness.py`
- Log observations after tool calls
- No changes to execution flow

**Value**: Immediate visibility into what agents "think"
**Risk**: None - pure data collection

**Step 2: Hypothesis Review Dashboard (Week 2)**
- Add UI to view hypotheses
- Show prediction vs observation
- Track confidence over time
- No changes to agent behavior

**Value**: Humans can see agent reasoning
**Risk**: None - read-only

**Step 3: Confidence Tracking (Week 3)**
- Track predicted confidence vs actual accuracy
- Calculate calibration metrics
- Show "surprise" when predictions are wrong
- No changes to agent behavior

**Value**: Learn how well agents predict
**Risk**: None - measurement only

**Step 4: Hypothesis-Driven Mode Selection (Week 4)**
- Make mode selection consider hypothesis confidence
- CURIOUS for low-confidence hypotheses
- SKEPTICAL for refuted hypotheses
- First behavior change

**Value**: Modes become hypothesis-aware
**Risk**: Medium - changes mode selection

### 3.3 Risk Areas

#### Risk 1: Hypothesis Overhead
**Problem**: Forcing hypotheses before every action might slow down simple tasks

**Mitigation**:
- Hypothesis formation is optional for low-risk actions
- Use "implicit hypotheses" with default predictions for common operations
- Cache hypotheses for repeated actions

#### Risk 2: Poor Hypothesis Quality
**Problem**: LLMs might form bad hypotheses or overconfident predictions

**Mitigation**:
- Start with low confidence requirements
- Use discriminating tests to catch bad predictions
- Calibrate confidence based on track record
- Human-in-the-loop for high-risk hypotheses

#### Risk 3: AHDB Bloat
**Problem**: Storing every hypothesis might explode the database

**Mitigation**:
- Only store hypotheses above confidence threshold
- Archive old hypotheses after N days
- Materialized views for asserted knowledge only
- Compact observation data with sampling

#### Risk 4: Breaking Existing Features
**Problem**: Changing core agent loop might break current functionality

**Mitigation**:
- Incremental rollout with feature flags
- Parallel execution (old and new paths) during transition
- Comprehensive regression tests
- Rollback plan for each phase

### 3.4 Testing Strategy

#### Phase 1: Unit Tests (Prediction & Observation)
```python
def test_hypothesis_formation():
    # Agent forms hypothesis before action
    hypothesis = form_hypothesis(context, action)
    assert hypothesis.prediction is not None
    assert 0.0 <= hypothesis.confidence <= 1.0
    assert hypothesis.discriminating_test is not None

def test_observation_logging():
    # Agent logs observation after action
    observation = log_observation(hypothesis, result)
    assert observation.prediction_match is not None
    assert observation.surprise_level is not None
```

#### Phase 2: Integration Tests (Hypothesis Lifecycle)
```python
def test_hypothesis_confirmed():
    # Correct prediction leads to confirmation
    store.create_hypothesis(prediction="X will happen")
    result = execute(experiment)
    assert store.get_hypothesis(status="confirmed")

def test_hypothesis_refuted():
    # Wrong prediction leads to refutation
    store.create_hypothesis(prediction="Y will happen")
    result = execute(experiment)  # Returns Z
    assert store.get_hypothesis(status="refuted")
```

#### Phase 3: System Tests (AHDB Learning)
```python
def test_ahdb_asserts_from_confirmed_hypotheses():
    # Confirmed hypotheses update AHDB
    initial_state = store.get_ahdb_state()
    run_experiment_sequence()
    final_state = store.get_ahdb_state()
    assert final_state != initial_state  # Learned something

def test_confidence_calibration():
    # Track prediction accuracy over time
    for _ in range(100):
        hypothesis = form_hypothesis()
        result = execute(experiment)
        log_prediction_accuracy(hypothesis, result)

    calibration = compute_calibration_metric()
    assert 0.7 <= calibration <= 1.3  # Well-calibrated
```

#### Phase 4: E2E Tests (Scientific Method)
```python
def test_agent_scientific_method():
    # Agent follows PREDICTION → EXPERIMENT → OBSERVE
    agent = AgentHarness()

    # PREDICTION
    hypothesis = agent.form_hypothesis("Reading file X will return content Y")
    assert hypothesis.confidence > 0.5

    # EXPERIMENT
    result = agent.run_experiment(hypothesis)

    # OBSERVE
    learning = agent.observe(hypothesis, result)
    assert learning.status in ["confirmed", "refuted"]

    if learning.status == "confirmed":
        assert store.get_ahdb_state()["file_X_exists"] == True
```

---

## Phase 4: The New ChoirOS

### 4.1 What Changes

#### Before: Task Runner
```
User prompt → Work item → Mode selection → Tool execution → Result
```

#### After: Hypothesis Engine
```
User prompt → Form hypothesis → Design experiment → Run experiment → Observe → Learn
```

### 4.2 Concrete Example

**Scenario**: User asks "Add a login button to the homepage"

**Current Flow**:
1. Work item created: "Add login button"
2. Mode selected: CALM
3. Agent: Reads files, edits code, runs tests
4. Result: Button added (maybe)
5. Receipt: "Wrote 3 files, tests passed"

**New Flow**:
1. **PREDICTION**:
   - Hypothesis: "Adding a login button to `src/App.tsx` at line 42 will render a clickable button"
   - Confidence: 0.8
   - Discriminating test: "If the button doesn't appear in the DOM, hypothesis is refuted"
   - Supporting evidence: "Button components exist in `src/components/`"

2. **EXPERIMENT**:
   - Mode: CALM (high confidence, low risk)
   - Action: Edit `src/App.tsx`, add `<Button>Login</Button>`
   - Verifiers: TypeScript check, visual regression test
   - Metrics: Render time, button visibility, click handler binding

3. **OBSERVE**:
   - Observation: Button appears in DOM, click handler works, tests pass
   - Prediction match: TRUE
   - Surprise level: 0.1 (as expected)
   - Confidence after: 0.9 (increased)

4. **LEARN**:
   - Hypothesis confirmed
   - AHDB assertion: `assert home_login_button_exists = True`
   - Evidence artifact: Screenshot hash, test report hash
   - Learning: "Buttons can be added to App.tsx at line 42"

**What's Different**:
- Every step is tracked as evidence
- We know what we predicted and what actually happened
- Confidence is calibrated
- AHDB stores assertions with evidence lineage
- If the button didn't appear, we'd know exactly why (discriminating test)

### 4.3 Agent Coordination via Hypotheses

**Scenario**: Multiple agents working on different parts of a feature

**Agent A** (Frontend):
- Hypothesis: "API endpoint `/api/user` will return user data"
- Confidence: 0.5 (uncertain if backend exists)
- Status: PENDING

**Agent B** (Backend):
- Hypothesis: "Creating `/api/user` endpoint will return user data"
- Confidence: 0.9 (has access to database)
- Status: CONFIRMED

**Coordination**:
1. Agent B confirms hypothesis → AHDB assertion: `assert api_user_endpoint_exists`
2. Agent A reads AHDB → Updates confidence to 0.9
3. Agent A runs experiment → Confirmed
4. AHDB assertion: `assert frontend_user_fetch_works`

**Result**: Agents coordinate through shared hypothesis registry, not explicit messaging

### 4.4 Mode Redefinition

**CALM**: Test specific predictions with low risk
- "I'm 90% sure this will work"
- Run experiment, verify, assert

**CURIOUS**: Form hypotheses about unknowns
- "I don't know, let's find out"
- Gather evidence, form conjectures

**SKEPTICAL**: Verify or refute existing hypotheses
- "You think that's true? Prove it."
- Run discriminating tests, challenge assumptions

**PARANOID**: Stress-test high-confidence hypotheses
- "You're 99% sure? What about edge cases?"
- Adversarial experiments, find refutations

**BOLD**: Scale confirmed hypotheses
- "This works here, will it work there?"
- Broaden scope, test generalizability

---

## Phase 5: Success Criteria

### 5.1 Quantitative Metrics

**Hypothesis Quality**:
- Average confidence calibration within ±0.2
- < 10% inconclusive hypotheses
- > 70% confirmation rate for high-confidence predictions

**Learning Rate**:
- AHDB assertions grow by > 5 per day (accumulated knowledge)
- Hypothesis refutation rate > 20% (learning from failures)
- Confidence convergence (predictions stabilize over time)

**System Performance**:
- < 5% overhead from hypothesis tracking
- < 100ms latency for hypothesis formation
- < 1s for observation logging

### 5.2 Qualitative Outcomes

**Developer Experience**:
- "I can see what the agent was thinking"
- "I know why it made this decision"
- "I can trace every assertion back to evidence"

**Agent Behavior**:
- Agents declare predictions before acting
- Agents revise beliefs when wrong
- Agents accumulate knowledge over time

**System Trust**:
- Every action has a rationale
- Every assertion has evidence
- Every failure produces learning

---

## Appendix: Migration Checklist

### Week 1: Data Collection
- [ ] Add `hypotheses` table to schema
- [ ] Add `hypothesis.created` event logging
- [ ] Add `hypothesis.completed` event logging
- [ ] Deploy to dev, validate data collection

### Week 2: Visibility
- [ ] Build hypothesis review UI
- [ ] Show predictions vs observations
- [ ] Track confidence over time
- [ ] Review hypothesis quality with team

### Week 3: Calibration
- [ ] Implement confidence tracking
- [ ] Calculate calibration metrics
- [ ] Add surprise detection
- [ ] Tune confidence thresholds

### Week 4: Behavior Change
- [ ] Hypothesis-driven mode selection
- [ ] CURIOUS for low confidence
- [ ] SKEPTICAL for refuted hypotheses
- [ ] A/B test against baseline

### Week 5-8: Agent Loop Redesign
- [ ] BAML `FormHypothesis` function
- [ ] BAML `ExtractLearning` function
- [ ] BAML `ReviseHypothesis` function
- [ ] Integrate into agent harness
- [ ] Gradual rollout with feature flags

### Week 9-12: Machine Redesign
- [ ] Replace work items with hypotheses
- [ ] Information gain prioritization
- [ ] AHDB as materialized view
- [ ] Full hypothesis-driven orchestration

### Week 13+: Optimization
- [ ] Performance tuning
- [ ] Hypothesis caching
- [ ] Evidence compression
- [ ] Confidence calibration refinement

---

## Conclusion

This redesign transforms ChoirOS from a task runner into a **scientific discovery engine**. Every action becomes an experiment, every prediction is tracked, and every outcome produces learning.

**The key insight**: PREDICTION/EXPERIMENT/OBSERVE is not a pattern - it's the protocol of intelligence itself. By making it the foundation of ChoirOS, we create a system that doesn't just do work, but **learns from every action it takes**.

**The migration path is incremental**: Start with data collection, add visibility, tune calibration, then gradually change behavior. Each phase delivers value independently, reducing risk.

**The end state**: A system where agents don't just execute tasks - they form hypotheses, run experiments, observe results, and accumulate knowledge. Not a task runner. A hypothesis testing engine.
