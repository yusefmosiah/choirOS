# TWP Spec: Taste-Weighted Promotion (Money × Security × Fairness × Fun)

This document specifies **Taste-Weighted Promotion (TWP)**: a mechanism for permissionless promotion of quarantined epistemic objects (claims, bindings, conjectures, hypertheses) into ASSERT-eligible canonical state, where **capital enables participation** but **taste determines upside**.

TWP integrates:
- **Money:** stake, vesting, slashing, fee markets
- **Security:** adversarial challenges, anti-collusion, invariant enforcement
- **Fairness:** “authority” derives from survival under scrutiny and independent reuse, not wallet size
- **Fun:** curator “whales” are recognized for selection skill; big fish subsidize the commons; challengers get bounties

---

## 0) Definitions

### Object types (atomic promotion targets)
Promotion is granular. The best unit is the **BINDING**.

- SOURCE: content-addressed source object (hash)
- EXTRACT: span/table object referencing source offsets (hash)
- CLAIM: normalized claim statement (hash)
- BINDING: (claim ↔ extract, relation, confidence) (hash)
- OMISSION: missing-but-relevant cluster pointer (hash)
- HYPERTHESIS: bounded blind spot / unsaid story (hash)
- CONJECTURE: (claim, test, edge, ΔO, scope) (hash)
- SYNTHESIS: report node referencing many atoms (hash)

### States
- UNTRUSTED: created, not eligible for global citation
- QUARANTINED: eligible for private use and review; not ASSERT-eligible
- PROMOTION-PENDING: collateral posted; challenge window open
- PROMOTED: ASSERT-eligible (can be referenced in ASSERT register and cited)
- RETRACTED: remains in history; no longer ASSERT-eligible (for cause)

### Actors
- PROMOTER: posts stake to move objects toward PROMOTED
- SPONSOR: funds verification throughput but is not necessarily rewarded for “taste”
- CHALLENGER: stakes to dispute promotion validity; earns if successful
- REFEREE: verifier ensemble + deterministic policy engine (small TCB)
- AUDITOR (RUN CALLER): pays credits to execute UNILATERAL_AUDIT endpoints

---

## 1) Design goals (explicit)

1) **Promotion buys scrutiny, not authority.**  
   A PROMOTE action is a request + collateral for review and challenge.

2) **ASSERT points only to PROMOTED atoms.**  
   No promoted atom → no ASSERT.

3) **Wallet size does not confer ranking or yield.**  
   Stake is eligibility + slashing exposure. Yield is taste-weighted.

4) **Taste is measurable predictive accuracy.**  
   “Whale” is a curator with high survival/utility under independent reuse.

5) **Attackers should have negative EV.**  
   Farming promotion yields should be dominated by slashing + vesting delays + anti-collusion penalties.

---

## 2) End-to-end pipeline

### Step A — RUN (permissionless; compute-paid)
UNILATERAL_AUDIT is called; it emits QUARANTINED atoms + receipts + verifier outputs.

### Step B — PROMOTE (permissionless; stake-paid)
Any account may select QUARANTINED atoms and submit a promotion bundle:
- promotion target(s) [atom hashes]
- stake amount
- optional rationale (non-authoritative)
- optional sponsor flag (fee-only)

Promotion transitions: QUARANTINED → PROMOTION-PENDING

### Step C — REVIEW (deterministic + ensemble)
Referee evaluates:
- required attestations exist (binding validity, reproducibility)
- policy invariants pass (no-copy, provenance)
- independence checks optional (re-run retrieval seeds / verifier variation)

If review fails, promotion is rejected (stake returned minus review fee).

### Step D — CHALLENGE WINDOW
During an open interval, challengers may stake challenges:
- specify target atom(s)
- provide counterevidence / invalidation proof
- trigger re-adjudication

### Step E — FINALIZE
If no successful challenges:
- PROMOTION-PENDING → PROMOTED
- promotion stake locks for vesting duration (or reduces over time)

If a challenge succeeds:
- PROMOTION-PENDING → QUARANTINED (or RETRACTED, depending on severity)
- promoter stake slashed (portion to challenger + insurance + protocol)

---

## 3) Taste-weighted rewards: the core mechanism

### 3.1 What is “taste”?
Taste is the capacity to select atoms that:
- remain valid under future scrutiny,
- are reused independently,
- reduce uncertainty (conjecture value),
- improve integrity (hyperthesis/reward-hack disclosures),
- and avoid collusive patterns.

### 3.2 Reward principle
**Yield is not proportional to stake. Yield is proportional to verified impact multiplied by promoter calibration.**

Formally, for promoter p and promoted atom i:

REWARD(p,i) = BASE(i) × IMPACT(i) × CALIBRATION(p) × DIVERSITY(p,i) × (1 − COLLUSION(p,i))  
then vested over time and subject to slashing for later invalidation.

Where:
- BASE(i) depends on atom type (binding > conjecture > hyperthesis > omission)
- IMPACT(i) is measured downstream (reuse + survival)
- CALIBRATION(p) is promoter taste score (predictive accuracy)
- DIVERSITY adjusts for cluster saturation and portfolio selectivity
- COLLUSION is a penalty derived from graph motifs and identity heuristics

Stake affects:
- whether you can promote,
- how much you can promote (bandwidth),
- and how much you lose if wrong.

Stake does not directly increase yield.

---

## 4) Computing IMPACT(i) (hard-to-farm)

IMPACT is determined by measurable downstream events, not by self-referential claims.

### 4.1 Impact signals (examples)
- INDEPENDENT REUSE: cited by other runs from unrelated tenants/lenses
- SURVIVAL: re-validated by verifier ensembles on reuse
- DISPUTE EFFECT: resolves challenges or flips verdicts
- COVERAGE EFFECT: reduces omission clusters over time
- SECURITY EFFECT: becomes a regression test or mitigates a known exploit pattern
- RETRIEVAL RETENTION: retrieved and retained after reranking and critic review

### 4.2 Anti-farming rules
- Citation cycles reduce IMPACT (graph cycle penalties)
- Reuse counts only if “independent” (different lenses, different callers, non-collusive graph distance)
- IMPACT saturates within a topic cluster (diminishing returns)
- External-anchor weighting (external sources > internal-only loops)

---

## 5) Computing CALIBRATION(p) (taste score)

### 5.1 Calibration as survival/utility accuracy
Promoter p selects atoms to promote. Each atom has an eventual outcome:
- VALID (survives and remains promoted)
- INVALIDATED (demoted/retracted by successful challenge)
- LOW-UTILITY (survives but never reused meaningfully)

Maintain a rolling score combining:
- survival rate
- time-to-falsification (faster falsification harms more)
- utility rate (independent reuse)
- challenge performance (ratio of successful vs unsuccessful promotions)
- “precision over recall” bias (selectivity rewarded)

A simple operational score:
- CALIBRATION(p) = sigmoid( a·Survival + b·Utility − c·Invalidation − d·CyclePenalty − e·SpamVolume )

### 5.2 Portfolio constraint
To prevent brute-force calibration gaming:
- Only top-K promotions per epoch contribute fully to calibration.
- Additional promotions contribute with diminishing weight.
This forces selectivity, the hallmark of taste.

---

## 6) Promotion bandwidth: capital is not the only constraint

### 6.1 Bandwidth tokens (non-transferable)
Each account has PROMOTION BANDWIDTH:
- increases with calibration over time
- decreases with failed promotions and spam flags

Stake can increase *review priority* but cannot override bandwidth limits.

### 6.2 Cluster quotas
A promoter cannot earn full yield by saturating one cluster.
- DIVERSITY(p,i) reduces rewards if p over-concentrates in a cluster.
This forces curators to seek new, valuable territory.

---

## 7) Sponsors vs curators

Sponsors provide throughput funding but are not paid for “taste” unless they also have calibration.

Two modes:
- SPONSOR MODE: pays review fees / funds verifiers; receives limited or no yield.
- CURATOR MODE: posts stake, accepts slashing, earns taste-weighted yield.

Sponsors can subsidize the commons without controlling epistemic authority.

---

## 8) Slashing, vesting, and insurance

### 8.1 Vesting
All rewards vest with a challenge window and delayed finality.
- Faster vesting for repeatedly re-validated atoms
- Slower vesting for high-risk categories (novel sources, new clusters)

### 8.2 Slashing
If a promoted atom is invalidated:
- promoter stake is slashed
- challengers earn bounties
- a portion goes to an insurance pool
- a portion funds verifier capacity

### 8.3 Insurance pool
Used for tail-risk incidents (systemic exploit). Triggered by explicit governance rules.

---

## 9) Ranking and retrieval: stake does not rank

PROMOTED is eligibility. Ranking is separate.

Ranking weight depends on:
- binding validity confidence
- independent reuse
- diversity
- recency where relevant
- anti-collusion penalties

Stake size is never a ranking feature; it is only an eligibility/collateral feature.

---

## 10) Whale vs big fish (the intended equilibrium)

- A **WHALE** is a high-calibration curator: few promotions, high survival and downstream reuse.
- A **BIG FISH** is high-capital, low-calibration: many promotions, low marginal yield, frequent slashing or low utility.

Big fish can still contribute by funding review (sponsor mode), but cannot buy epistemic authority.

---

## 11) Integration with AHDB embeddings and state evolution

The system embeds:
- AHDB state notes (assert/hypothesize/drive/believe)
- hypertheses and conjectures
- promotion/challenge outcomes

This improves:
- retrieval alignment (situation similarity, not topic similarity)
- security pattern matching (tactic similarity)
- scam detection (lack of marginal meta-value; repetitive low-utility state)

Rewards can also be paid for:
- novel, later-confirmed hypertheses (security disclosures)
- conjectures that shrink blind spots via ΔO adoption
- verifier improvements derived from successful challenges

---

## 12) Minimal parameter set (v0)

To implement TWP minimally, choose:
- Challenge window duration (per risk tier)
- Vesting schedule (base + acceleration on revalidation)
- Slashing fractions (challenger / insurance / protocol)
- Calibration function weights (a,b,c,d,e)
- K: top promotions per epoch fully counted (portfolio selectivity)
- Cluster saturation thresholds (diversity penalty schedule)

Start conservative; increase freedom only after adversarial learnings.

---

## 13) Summary: the one-line spec

PROMOTE is permissionless collateralized scrutiny.  
ASSERT cites only PROMOTED atoms.  
YIELD is taste-weighted by survival and independent reuse, not stake size.  
CHALLENGE is permissionless, and slashing funds defenders.  
BIG FISH subsidize; WHALES curate.

---

This spec is meant to be implemented incrementally. The earliest safe version is:
- PROMOTE as stake-gated review + challenge
- PROMOTED as ASSERT-eligible only after attestations
- rewards vested and heavily delayed, tied to reuse and survival
- calibration score and portfolio caps to force selectivity
