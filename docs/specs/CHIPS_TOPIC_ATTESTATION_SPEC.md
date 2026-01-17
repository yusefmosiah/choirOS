# CHIPS + TOPIC STREAMS + ATTESTATION MARKET Spec (for TWP)

This document formalizes an initial mechanism design for:
1) **CHIPS** (credits/gas for Choir Harmonic Intelligence Platform),
2) **TOPIC STREAMS** (subscribable event channels for artifacts and claims),
3) **ATTESTATION MARKET** (permissionless verification work with delayed rewards),
and how these compose with **TWP (Taste-Weighted Promotion)**.

The design goal is to bootstrap usage with chips grants while keeping authority, ranking, and rewards robust under adversarial pressure.

---

## 0) High-level doctrine

- **CHIPS buy computation and scrutiny.** (RUN and ATTEST)
- **STAKE buys credibility insertion.** (PROMOTE and slashing exposure)
- **REWARDS pay for survival and impact over time,** not raw activity.
- **ASSERT may cite only PROMOTED atoms,** and PROMOTE requires attestations.

---

## 1) Core objects and states

### 1.1 Atomic objects (promotion targets)
(See TWP spec for full list; these are the main ones in the chips/attestation loop.)

- SOURCE(hash)
- EXTRACT(hash; references source offsets)
- CLAIM(hash)
- BINDING(hash; claim↔extract with relation)
- OMISSION(hash; missing cluster)
- HYPERTHESIS(hash; bounded blind spot / disclosure)
- CONJECTURE(hash; claim+test+edge+ΔO+scope)

### 1.2 Object lifecycle states
- **UNTRUSTED**: ingested or proposed; not citable
- **QUARANTINED**: available for review; not ASSERT-eligible
- **PROMOTION-PENDING**: stake posted; challenge window open
- **PROMOTED**: ASSERT-eligible; citable (subject to later retraction)
- **RETRACTED**: historically retained; not ASSERT-eligible

---

## 2) CHIPS: credits/gas for platform work

### 2.1 What CHIPS pay for (sinks)
CHIPS are consumed by:
- **RUN**: executing UNILATERAL_AUDIT (retrieval + synthesis + verifiers)
- **ATTEST**: producing attestations (binding validity, omission checks, revalidations)
- **RED-TEAM** (optional): adversarial checks (critic runs, exploit probes)
- **REVIEW** (optional): additional referee passes (if not fully subsidized by stake)

CHIPS are *not* used to directly buy rank or authority.

### 2.2 Chip grants (bootstrapping)
Early users receive periodic chip grants subject to:
- identity/rate-limits (anti-sybil)
- per-epoch caps
- topic diversity encouragement (optional)
- reduced grants for accounts flagged by anomaly detectors

### 2.3 Chip accounting
Every chip spend must emit a receipt:
- payer identity
- action type (RUN/ATTEST/RED-TEAM/REVIEW)
- budget parameters (caps)
- hash pointers to affected objects
- verifier versions and outcomes (where applicable)

### 2.4 Chip pricing and throttles
- Base prices can vary by task class (e.g., heavy web retrieval vs KB-only).
- Dynamic pricing may be applied when verifier throughput is saturated.
- Hard caps protect system: max web fetches, max tokens, max wall time per RUN.

---

## 3) UNILATERAL_AUDIT endpoint (permissionless)

### 3.1 Endpoint overview
**UNILATERAL_AUDIT(target, lens, budgets, privacy_mode)**

Consumes CHIPS and produces:
- QUARANTINED atoms (claims, bindings, hypertheses, conjectures)
- receipts (context footprint, evidence-set hash, verifier versions)
- optional draft synthesis artifacts (non-citable unless promoted)

### 3.2 Outputs must be typed and content-addressed
- No raw-copy dumping (NO-COPY enforced)
- Evidence references are pointers (hash+span), not pasted text

### 3.3 Default output state
All outputs are **QUARANTINED** by default.
Promotion is separate and voluntary (TWP).

---

## 4) TOPIC STREAMS: subscribable event channels

### 4.1 Definition
A TOPIC STREAM is an append-only event channel that emits:
- new QUARANTINED atoms relevant to a topic
- promotion events (pending/promoted/retracted)
- challenge events and outcomes
- revalidation needs (staleness, drift, controversy spikes)

### 4.2 Topic taxonomy
- Topics should be hierarchical (topic → subtopic → tags)
- Each atom can belong to multiple topics with confidence scores
- Topic assignment is advisory; promotion and attestations remain binding-level

### 4.3 Subscriptions
An actor may SUBSCRIBE(topic, mode, budget):
- mode = {ATTESTER, CHALLENGER, SPONSOR, OBSERVER}
- budget = chip budget and rate limits
- optional filters (risk tier, novelty threshold, only-promoted, only-quarantine)

### 4.4 Routing rules (independence by design)
To reduce collusion and correlated failure:
- The system preferentially routes the same atom to **independent** subscribers:
  - different identities/tenants
  - different retrieval seeds (where applicable)
  - different verifier ensembles or models
- Subscribers do not receive each other’s intermediate notes by default.

---

## 5) ATTESTATION MARKET: permissionless verification work

### 5.1 Attestation types
At minimum:
- **BINDING_VALIDITY**: entailment/localization pass/fail for a binding
- **OMISSION_CHECK**: missing cluster identification and evidence pointers
- **REVALIDATION**: re-run checks under new snapshot/retriever versions
- **SECURITY_DISCLOSURE**: reward-hack / injection pattern note (hyperthesis)

Each attestation is a content-addressed object:
ATTESTATION(hash) = {target_atom_hash, attestation_type, inputs_hash, result, verifier_version, receipt}

### 5.2 Attestation requires CHIPS
ATTEST consumes CHIPS; therefore, chips grants bootstrap verification throughput.

### 5.3 Immediate vs delayed compensation
Two channels:
- **WORK COMP** (optional, small): pays for verified computation contribution.
- **IMPACT COMP** (primary): vests over time based on downstream survival and reuse of the attested atom.

The default safe posture is:
- minimal or zero WORK COMP initially,
- strong delayed IMPACT COMP.

### 5.4 Attester calibration (taste for verification)
Attesters have a **CALIBRATION score** based on:
- agreement with later challenge outcomes
- agreement with independent revalidations
- low false-positive challenge rate (if they also challenge)
- contribution to high-utility promoted atoms

Calibration affects:
- allowed attestation bandwidth
- priority routing
- reward multipliers on IMPACT COMP

Calibration does **not** grant authority to assert; only attestations do.

---

## 6) Composition with TWP Promotion

### 6.1 Promotion prerequisites (policy)
Promotion should require:
- at least one valid BINDING_VALIDITY attestation for each promoted binding
- optional independent attestations for higher risk tiers
- NO-COPY compliance for promoted syntheses
- hyperthesis disclosure for high-impact claims (bounded blind spots)

### 6.2 Promotion is voluntary and permissionless
- Any actor can stake to promote atoms (curator role).
- Curator yield is taste-weighted (TWP).

### 6.3 Shared upside for prior attesters
If an atom they attested becomes PROMOTED and then generates impact:
- Attesters earn a share of IMPACT COMP (delayed)
- Promoters earn taste-weighted yield (delayed)
- Challengers earn bounties for successful invalidations

This creates a compounding incentive triangle:
ATTEST → PROMOTE → REUSE → PAY (or CHALLENGE → SLASH)

---

## 7) Challenge and slashing loop

### 7.1 Challenge as security primitive
Any PROMOTION-PENDING or PROMOTED atom can be challenged.
Challenge requires:
- challenger stake
- counterevidence pointers or verifier failures
- re-adjudication by referee ensemble

### 7.2 Outcomes
- Successful challenge → demotion/retraction + promoter slashed; challenger paid.
- Unsuccessful challenge → challenger stake partially slashed (anti-spam).

### 7.3 Insurance pool
A fraction of slashing flows to an insurance pool for systemic incidents.

---

## 8) Anti-spam and anti-whale capture (core constraints)

### 8.1 Stake does not rank
Ranking/retrieval uses:
- binding validity confidence
- independent reuse/survival
- diversity penalties
- anti-collusion graph penalties

Stake is eligibility + slashing exposure only.

### 8.2 Diminishing returns on activity
- Only top-K promotions per epoch count strongly (TWP portfolio cap).
- Only top-K attestations per epoch count strongly for calibration boosts (optional).
- Topic cluster saturation reduces marginal yield and impact.

### 8.3 Independence heuristics
- Penalize cycles in citation graphs.
- Discount reuse that occurs within tight identity clusters.
- Encourage cross-tenant/lens reuse.

---

## 9) v0 parameter defaults (suggested)

These are starting points, not commitments.

- Chip grants: small, capped, renewable weekly; higher for high-calibration users.
- RUN budgets: strict max web pages, strict token caps; multi-stage expansion requires explicit opt-in.
- Attestation budget: cheap model tiers for first-pass validity; stronger model tiers only on disputes.
- Promotion challenge window: short for low-risk atoms, longer for high-risk atoms.
- Vesting: long by default; accelerated by independent reuse and revalidation survival.
- Slashing: meaningful; enough to make spam negative EV.

---

## 10) End-to-end flow examples

### Example A — A user runs an audit
1) User pays CHIPS to RUN UNILATERAL_AUDIT.
2) System outputs QUARANTINED claims/bindings/hypertheses.
3) Attesters subscribed to the topic see new atoms and spend CHIPS to attest.
4) A curator stakes to PROMOTE specific bindings.
5) Challenge window passes; bindings become PROMOTED.
6) Future audits reuse those bindings; survival and reuse trigger delayed rewards.

### Example B — A whale tries to promote everything
- They can post stake, but:
  - yield is not proportional to stake,
  - calibration and portfolio caps limit upside,
  - low-quality promotions get challenged and slashed,
  - cluster saturation and collusion penalties reduce impact.
Result: they either learn taste or become a sponsor (subsidizing the commons).

---

## 11) What “ASSERT” means under this system

ASSERT is never a reference to arbitrary data. It is a reference to PROMOTED atoms only:
- PROMOTED bindings
- PROMOTED conjectures/hypertheses (as security state notes)
- PROMOTED sources/extracts (as admissible evidence pointers)

Everything else remains QUARANTINED and can be used for reasoning but not for authoritative citation.

---

## 12) Minimal implementation checklist

To implement v0:
1) Content-addressed object store (sources, extracts, bindings, receipts).
2) UNILATERAL_AUDIT endpoint with QUARANTINED outputs.
3) Topic stream routing + subscriptions.
4) Attestation objects + verifier execution.
5) Promotion state machine (pending/promoted/retracted) with challenge windows.
6) Delayed reward accounting tied to reuse/survival (even if rewards are initially off).
7) Anti-collusion graph metrics and basic anomaly detection.

---

This spec is designed to be compatible with:
- AHDB state embeddings (for retrieval and scam detection),
- TWP promotion (taste-weighted yield),
- and defense-in-depth security (attestations + challenges + receipts).
