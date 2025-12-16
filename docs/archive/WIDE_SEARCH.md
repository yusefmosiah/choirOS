# When to Go Wide: Fanout Agent Search

> In what circumstances might we want 1024 agents exploring in parallel?

---

## The Economics of Width

Single agent: pay once, get one path.
N agents: pay N times, get N paths, then pay to merge.

Wide search is worth it when:
```
E[value of best path] - E[value of single path] > cost of (N-1) agents + merge
```

This is positive when:
- Variance between paths is high (creative work, search)
- Single path has significant failure probability
- Merge is cheap relative to generation
- You need confidence, not just an answer

---

## Candidate Triggers for Full-Width Search

### 1. Creative Exploration

**Signal:** "Write a poem about X" / "Design a logo" / "Come up with names for Y"

**Why wide:** Creative work has no single correct answer. More attempts = more options. User wants to *choose*, not receive.

**Width:** 10-50 (not 1024—diminishing returns on creativity)

**Merge:** User picks favorites. No algorithmic merge.

---

### 2. Adversarial Robustness / Red Team

**Signal:** "Check this for problems" / "Find vulnerabilities" / "What could go wrong?"

**Why wide:** Different agents will find different failure modes. Ensemble catches more than any single critic.

**Width:** 10-100 (each with different "attacker persona")

**Merge:** Union of all discovered issues. Dedupe by similarity.

---

### 3. Calibration / Confidence Estimation

**Signal:** "How sure are you?" / "Is this definitely true?" / User asking about facts where hallucination risk is high.

**Why wide:** Run the same query N times. If answers diverge, confidence is low. If they converge, confidence is higher.

**Width:** 5-20 (statistical, not exhaustive)

**Merge:** Report distribution. "8/10 agents said X, 2 said Y."

---

### 4. Explicit Search / Enumeration

**Signal:** "Find all the ways to..." / "What are my options for..." / "Search for X"

**Why wide:** Each agent explores a branch. Classic tree search parallelized.

**Width:** Scales with search space. Could be 1024 for large spaces.

**Merge:** Collect all results, rank/filter.

---

### 5. Code Generation with Tests

**Signal:** "Write a function that does X" (where X has test cases)

**Why wide:** Generate N implementations, run tests on each, return those that pass. Genetic algorithm vibes.

**Width:** 50-200 (more = more likely to find working solution)

**Merge:** Filter by test pass. Rank by other criteria (speed, readability).

---

### 6. Research with Citation Verification

**Signal:** "What does the evidence say about X?" / Anything where grounding matters.

**Why wide:** Each agent researches independently. Cross-check citations. Disagreement reveals uncertainty or conflicting sources.

**Width:** 5-20

**Merge:** Synthesize with explicit disagreement reporting. "Agents A, B, C found evidence for X. Agent D found counterevidence."

---

### 7. Planning Under Uncertainty

**Signal:** "How should I approach X?" (complex, multi-step, unclear)

**Why wide:** Different agents will propose different plans. Some will be better for certain scenarios. Monte Carlo planning.

**Width:** 10-50

**Merge:** Present as options with tradeoffs. Or: simulate each plan forward, evaluate outcomes.

---

### 8. Negotiation / Multi-Perspective

**Signal:** "What would [different stakeholders] think about this?"

**Why wide:** Each agent adopts a different persona/perspective. Explicit roleplay parallelized.

**Width:** Number of stakeholders (often 3-10)

**Merge:** Report each perspective separately. Synthesis optional.

---

## When NOT to Go Wide

### Single-Path Problems

"What's the capital of France?" — there's one answer. Width is waste.

### Latency-Critical

If user needs a response in 2 seconds, can't wait for 1024 agents to complete.

### High Merge Cost

If combining results requires as much work as generating them, width doesn't help.

### Homogeneous Outputs

If all N agents will say roughly the same thing (low temperature, deterministic problem), width adds cost without diversity.

---

## The UI Question

How does 1024-wide search appear on the shared canvas?

**Option A: Swarm View**

A special window showing many small tiles, each an agent. Activity pulses. Click to expand one.

```
┌─────────────────────────────────────────────────┐
│  Exploring: "Design approaches for X"           │
│  ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐    │
│  │ ▪ │ │ ▪ │ │ ▪ │ │ ✓ │ │ ▪ │ │ ▪ │ │ ✗ │    │
│  └───┘ └───┘ └───┘ └───┘ └───┘ └───┘ └───┘    │
│  12 running • 3 complete • 1 failed             │
└─────────────────────────────────────────────────┘
```

**Option B: Results Stream**

Single window, results append as agents complete. Like search results.

**Option C: Background + Notification**

"Exploring 50 approaches... will notify when ready."

Fanout happens invisibly. Toast when done. Results appear as artifact.

**Option D: Tree Visualization**

If search is hierarchical, show the tree being explored. Branches expand as agents work.

---

## Implementation Sketch

```typescript
interface FanoutRequest {
  prompt: string;
  width: number;                    // how many agents
  strategy: 'creative' | 'search' | 'calibration' | 'adversarial';
  merge: 'user_picks' | 'vote' | 'judge' | 'union' | 'none';
  constraints?: {
    maxCost?: number;
    maxTime?: number;
    stopOnSuccess?: boolean;        // for test-based search
  };
}

interface FanoutResult {
  id: string;
  status: 'running' | 'complete' | 'partial';
  agents: AgentResult[];
  merged?: Artifact;                // if merge strategy produces one
  stats: {
    started: number;
    completed: number;
    failed: number;
    agreement?: number;             // for calibration
  };
}
```

---

## The Deep Question

You asked: "in what circumstance might we want full width?"

The deepest answer: **when you want to simulate a market.**

Markets aggregate information from many independent actors. Each agent is a "trader" with its own view. The "price" (merged result) reflects collective intelligence better than any single actor.

1024 agents exploring = 1024 independent perspectives being aggregated.

This is expensive. But for high-stakes decisions where being wrong is costly, it might be cheap.

---

## Choir-Specific Insight

The citation economy already does this *asynchronously*.

- Many humans publish artifacts
- AI agents cite them
- Citations aggregate quality signal
- Good ideas surface

Wide-agent search is the *synchronous* version:
- Many agents generate in parallel
- Merge/vote aggregates quality signal
- Good outputs surface

The citation graph is slow-wide-search. Fanout is fast-wide-search. Same principle, different timescale.

---

*This document is exploratory. None of this is decided.*
