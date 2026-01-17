# The Automatic Computer: Security Models

This document describes the security posture of the “Automatic Computer” over time: how we start safe, how we harden under adversarial pressure, and what capability gates must be satisfied before we expand privileges (including cryptographic signing and capital allocation).

The system’s core advantage is tempo: a director/associate control loop operating across isolated trust zones, with event sourcing and compounding knowledge enabling rapid detection, replay, and repair.

## 1. Design principles

1) Minimize the trusted computing base (TCB).  
The smallest possible components should be able to approve privileged actions (publishing into canonical memory, distributing rewards, signing transactions). LLM agents are not part of the TCB.

2) Assume adversaries and Goodhart’s law.  
Any measurable objective will be optimized against. Security and grading must be designed as adversarial systems.

3) Separate planning from execution; separate content from control.  
The director owns policy, orchestration, and privilege escalation. Associates execute bounded work items. Untrusted content never directly influences control decisions.

4) Everything is replayable.  
Every decision and side-effect is captured in an append-only event log. All “current state” is a projection.

5) Defense in depth with asymmetric cost.  
Attacks should be expensive to scale; detection and mitigation should be cheap and automated.

6) Blast radius is bounded by default.  
Per-tenant limits, quarantine stages, time locks, and circuit breakers prevent single incidents from becoming systemic failures.

## 2. Threat model

We treat the Automatic Computer as operating in an adversarial environment from the first day incentives or persistence exist.

Primary threat classes:

A) Prompt injection and instruction smuggling  
Untrusted inputs (web pages, documents, user-provided text) attempt to influence agent behavior, tool use, or approvals.

B) Reward hacking and metric gaming  
Actors attempt to maximize rewards without creating real epistemic value (citation stuffing, novelty spam, internal citation rings, retrieval poisoning).

C) Knowledge base poisoning  
Attacks attempt to insert misleading or low-quality artifacts into the compounding memory to influence future audits, retrieval, or grading.

D) Sandbox and supply-chain compromise  
Attempts to escape execution sandboxes, exploit dependencies, exfiltrate secrets, or tamper with verifiers.

E) Identity and Sybil attacks  
Mass account creation and collusion to farm rewards or manipulate ranking.

F) Financial attack surface (later stage)  
MEV manipulation, oracle attacks, fake sources driving trades, signing perimeter compromise, governance capture.

We explicitly plan for “unknown unknowns” by investing in continuous red teaming, anomaly detection, and rapid rollback/quarantine.

## 3. Core security architecture

### 3.1 Trust zones

The system is partitioned into zones with strictly controlled interfaces:

1) Untrusted Ingestion Zone  
Fetch/parse/normalize untrusted content (URLs, PDFs, HTML, connectors).  
Privileges: read-only external access (allowlisted egress), no secrets, no KB publishing, no payouts.

2) Verification Zone  
Runs verifiers that convert untrusted content into structured attestations (evidence bindings, entailment checks, contradiction checks, omission checks).  
Privileges: limited reads, generates attestations only (no direct publishing/rewards).

3) Publishing Zone  
Synthesizes user-facing artifacts (reports, critiques, summaries) that can be stored in a quarantine index.  
Privileges: write to quarantine index only, never to canonical memory directly.

4) Reward & Governance Zone  
Computes scores, handles staking/vesting/slashing, resolves challenges, and governs promotion of artifacts.  
Privileges: consumes only attestations and content hashes; never consumes raw untrusted content.

5) Signing Perimeter (financial stage only)  
A minimal TCB service that produces cryptographic signatures only upon receiving a policy-approved approval token tied to immutable evidence (memo hash + verifier hashes + approval thresholds).  
Privileges: key material never accessible to agents; multi-sig/MPC/HSM-backed.

### 3.2 Director/associate pattern

Director (control plane actor)
- Owns routing across zones, model selection, budgets, permissions, and policy decisions.
- Spawns specialized subagents (retrieval, critique, red team) when complexity requires.
- Produces approval tokens and escalation packets (including human 2FA packets).

Associate (data plane worker)
- Executes a single bounded work item in a sandbox with explicit constraints.
- Cannot change policy, cannot approve privileges, cannot publish directly to canonical state.
- Reports outcomes as events plus artifacts.

### 3.3 Dual sandboxing

We operate at least two sandbox classes:

A) Ingestion Sandboxes  
Hardened for hostile inputs; minimal tooling; strict network allowlists; no credentials.

B) Execution/Validation Sandboxes  
Hermetic builds where possible; pinned toolchains; restricted filesystem; constrained tool set; no ambient secrets (leases only).

For higher-risk operations, we add an additional “referee sandbox” that independently re-runs verifications to avoid single-sandbox compromise.

### 3.4 Event sourcing and receipts

All meaningful actions emit events:
- Inputs ingested (hashes, provenance)
- Tool calls and outputs (summarized + hashed)
- Verifier results (structured attestations)
- Policy decisions (why, thresholds, approvals)
- Publications (artifact hashes, promotion state)
- Rewards (score components, vesting schedule)
- Challenges and outcomes
- Signing requests and signatures (financial stage)

Every privileged action must carry a receipt: a compact, machine-checkable bundle referencing immutable hashes of its inputs, attestations, and approvals.

## 4. Security maturity model (capability unlocks)

Security increases by unlocking privileges only after measured integrity gates pass. Each stage also increases adversarial pressure; defenses must therefore compound faster than attacks.

### Stage 0: Local deterministic agents (no incentives, no persistence risk)
Scope: coding agents and validation loops.  
Controls:
- single-repo sandboxes
- strong verifiers (tests/types/lint)
- replayable event log
Gates to advance:
- repeatable runs; stable rollback; bounded iteration and diff size

### Stage 1: Platform engineering (multi-agent orchestration)
Scope: director/associate + trust zones + policy engine.  
Controls:
- capability-based permissions
- dual sandboxes
- circuit breakers and quarantine
- secrets as time-bound leases
Gates to advance:
- proven isolation boundaries; kill switches; comprehensive observability

### Stage 2: Compounding auditor (knowledge base with quarantine promotion)
Scope: unilateral auditor and content integrity.  
Controls:
- claim–evidence binding schema
- entailment/localization checks
- independent omission discovery pipeline
- contradiction checks vs KB
- quarantine index + promotion gates
Gates to advance:
- high binding integrity; low KB pollution; demonstrable adversarial robustness

### Stage 3: Rewards in an adversarial economy (native token, no signing)
Scope: crypto incentives for content integrity contributions.  
Controls:
- stake-to-submit; stake-to-challenge
- vesting + challenge window
- slashing for provable invalid bindings and collusion
- payout circuit breakers on anomaly triggers
Gates to advance:
- negative expected value for farming; rapid exploit-to-mitigation cycle; stable governance

### Stage 4: Native-asset allocation (signing requests under strict policy)
Scope: financial actions limited to the native asset; “bet on your ideas.”  
Controls:
- signing request API with mandatory evidence memo
- adversarial evaluation (counter-memo) in separate zone
- deterministic policy engine with time locks
- human 2FA on threshold/category changes
- post-action reconciliation and thesis tracking
Gates to advance:
- sustained incident-free operation; verified containment; mature red/blue automation

### Stage 5: Multi-asset fund management (tokenized fund)
Scope: external assets and broader strategy set.  
Controls:
- signing perimeter hardened (MPC/HSM/multi-sig, timelocks)
- strict allowlists and risk budgets
- oracle integrity and NAV methodology
- MEV controls and simulation requirements
- explicit insurance fund triggers and caps
Gates:
- continuous; security becomes an operating discipline rather than a “milestone”

## 5. Red/blue self-play: one adversarial engine for code and content

We unify two games:
- Content integrity: proposer report vs adversary falsifier (citation validity/omissions)
- Code integrity: proposer patch vs adversary security tester (vuln/regression)

Shared primitives:
- Atomic commitments (claim↔evidence; patch↔spec)
- Permissionless challenges with proofs
- Referee adjudication
- Regression growth: every successful attack becomes a new test / detector
- Economic incentives (later): pay for verified vulnerabilities and verified falsifications

This creates asymmetric defense: defenders can reuse discovered attack patterns immediately, while attackers must constantly innovate.

## 6. Observability and auto-remediation

### 6.1 Agentic observability

We monitor:
- citation binding integrity rate
- omission recall stability
- novelty distribution shifts (spam indicators)
- citation graph motifs (cycles, rings, mutual citation)
- per-tenant anomaly scores
- sandbox policy violations and near-misses
- verifier disagreement rates (ensemble drift)
- reward distribution anomalies and payout concentration

### 6.2 Automated circuit breakers

Triggered responses include:
- freezing promotion to canonical KB for affected clusters/tenants
- freezing payouts for affected clusters/tenants
- tightening validation thresholds and increasing ensemble redundancy
- forcing human 2FA for categories flagged as risky
- re-running audits in referee sandboxes
- rolling back projections to a prior safe checkpoint

## 7. Incentives, economics, and insurance

### 7.1 Incentive design

We reward:
- Valid evidence bindings (precision-weighted, not count-weighted)
- Material omissions correctly identified
- Successful adversarial falsifications (security and content)
- Downstream utility (retrieval and reuse), discounted for internal cycles

We penalize:
- invalid bindings
- content spam and novelty noise
- collusion rings and Sybil patterns
- policy violations and sandbox boundary probes

### 7.2 Vesting and slashing

Rewards vest with a challenge window.  
Slashing is targeted at atomic commitments to make enforcement cheap and precise.

### 7.3 Insurance fund

The insurance fund exists for tail risks and classified incidents (e.g., verified systemic exploit, infrastructure escape). It is governed by:
- explicit incident categories and validation methods (ledger proofs)
- caps per incident and per user
- automatic conservative-mode triggers after drawdowns

## 8. Non-goals and constraints

- We do not attempt perfect security in the theoretical sense. We aim for bounded blast radius, rapid detection, and rapid iteration.
- LLM behavior cannot be fully predicted from arbitrary inputs; therefore we design with isolation, redundancy, and economic finality.
- “Open source” does not mean every detection heuristic is predictable at runtime; some adversarial tests and canaries may be committed via delayed disclosure.

## 9. What “secure enough” means operationally

Before unlocking higher privilege stages, we require:
- measurable integrity under optimization pressure (adversarial testing results)
- bounded economic exposure (caps + vesting + slashing)
- fast mitigation loops (exploit-to-guardrail cycle time)
- replayable incident postmortems from the event log
- credible quarantine and rollback in production

Security is not a static claim; it is a compounding capability. The Automatic Computer’s strategy is to compound faster than attackers by combining trust zones, adversarial self-play, and an event-sourced memory of every incident and fix.
