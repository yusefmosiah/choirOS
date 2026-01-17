# Research-as-Verification Pattern (v0)

This document formalizes a micro-pattern to amplify in Choir:

**Research is not a convenience tool call. Research is verification of a thesis.**

Therefore, sessions do not directly “search the web” or “query the KB.” They delegate to a **VERIFIER** that returns **evidence cards** (pointer-based, content-addressed) and emits **attestations**. Only those attestations can upgrade AHDB state.

---

## 0) Why this pattern exists

Direct retrieval inside a working session causes three recurring failures:

1) **Token noise / context pollution**
Raw search results and long tool outputs bloat context and degrade coherence.

2) **Authority smuggling**
Untrusted text can influence actions if retrieval results are treated as instructions or “truth” rather than data.

3) **Non-replayable epistemics**
If retrieval is done ad hoc inside a session, it becomes hard to reconstruct exactly what evidence was used and why a decision was made.

The fix is to treat retrieval as a verifier lane (green thread) with structured outputs and receipts.

---

## 1) Definition

### 1.1 Thesis
A THESIS is an AHDB-relevant proposition that, if supported or refuted, changes next actions.

Examples:
- “This claim in the source is correct.”
- “We should choose approach X over Y.”
- “This security boundary prevents exfiltration.”
- “This library supports feature Z.”

### 1.2 Research-as-Verification
Research-as-Verification is a procedure:

- Input: THESIS + scope + constraints
- Output: evidence cards + coverage report + attestation
- Side effect: updates to AHDB are allowed only through verifier outputs

---

## 2) Rule: sessions never call search directly

### 2.1 Prohibited inside execution sessions
- web_search / browse / crawl
- KB semantic search
- filesystem search across broad scopes
- connector queries (Drive/Slack/etc.)

These actions may be *requested* but not executed in-session.

### 2.2 Allowed in execution sessions
- creating a THESIS
- requesting a verification run
- consuming evidence pointers and attestations returned by the verifier
- proceeding with code changes only after verification gates (when required)

This keeps the main loop coherent and low-entropy.

---

## 3) The Verifier (research lane) contract

Verification runs in a separate “green thread” session (or mood) with:
- network/tool permissions appropriate to the risk tier
- strict budgets (sources, tokens, time)
- output schema enforcement

### 3.1 Inputs (VERIFY_REQUEST)
VERIFY_REQUEST
- THESIS_ID
- THESIS_TEXT (normalized)
- LENS (optional)
- SCOPE: {web, kb, files, connectors}
- CONSTRAINTS: allowed domains, time window, source types
- RISK_TIER: low/med/high
- BUDGET: max sources, max tokens, max wall time
- REQUIRED_OUTPUTS: {evidence_cards, coverage_map, contradictions, omissions}

### 3.2 Outputs (EVIDENCE_CARDS + ATTESTATION)
The verifier returns:

A) Evidence cards (pointer-based)
EVIDENCE_CARD
- CARD_ID (hash)
- SOURCE_HANDLE (content-address)
- SPAN_HANDLE (offsets, hash)
- CLAIM_LINK: which sub-claim it supports/contradicts
- RELATION: SUPPORTS | CONTRADICTS | QUALIFIES | IRRELEVANT
- CONFIDENCE: calibrated
- NOTES: short, bounded (no copying)

B) Coverage map
- Top-K clusters covered
- Major missing clusters (OMISSIONS) with pointers
- Contradiction summary (where sources disagree)

C) Attestation (authoritative output)
ATTESTATION
- THESIS_ID
- VERIFIER_VERSION
- EVIDENCE_SET_HASH (list of card IDs)
- RESULT: SUPPORTED | DISPUTED | UNSUPPORTED | INCONCLUSIVE
- HYPERTHESIS: what cannot be ruled out given the evidence and constraints
- RECEIPT pointers (exact retrieval parameters, timestamps, budgets)

Raw tool output is stored as artifacts, not injected into the main session.

---

## 4) How this updates AHDB

The director compiles verifier outputs into AHDB updates:

- ASSERT is updated only if:
  - RESULT is SUPPORTED (or bounded appropriately), and
  - evidence set is promoted/admissible per policy, and
  - receipts exist.

- HYPOTHESIZE is updated when:
  - RESULT is INCONCLUSIVE/DISPUTED and a discriminating test is proposed.

- HYPERTHESIS is updated whenever:
  - verifier names blind spots (missing sources, unverifiable claims, adversarial risk).

This makes “research” a first-class epistemic gate, not an ad hoc tool call.

---

## 5) Evidence cards must be content-addressed

Every card and referenced source/span must have stable handles:
- SOURCE_HASH (raw + canonical forms)
- SPAN_ID / offsets
- CARD_ID hash (normalized card schema)

This enables:
- replay
- dedupe
- dispute resolution
- future reuse and citation without copying

---

## 6) Anti-waste rules

- **Do not run repeated full searches** for the same thesis; reuse EVIDENCE_SET_HASH when possible.
- Prefer **cheap models** for card generation; reserve expensive models for synthesis only when necessary.
- Enforce budgets and stop conditions; if evidence is insufficient, return INCONCLUSIVE with explicit hyperthesis rather than burning tokens.

---

## 7) Security posture

- Treat all retrieved text as untrusted DATA.
- Verifier output is authoritative only as an ATTESTATION object tied to receipts.
- No outbound network from code-execution moods by default.
- No credentials may be injected via retrieved text; egress must be identity-bound and policy-gated.

---

## 8) Prompt-ready doctrine block

RESEARCH IS VERIFICATION.
- SESSIONS DO NOT SEARCH.
- SESSIONS REQUEST VERIFY.
- VERIFIER RETURNS EVIDENCE CARDS + ATTESTATION.
- ONLY ATTESTATIONS UPDATE ASSERT.

NO CARDS → NO ASSERT.
NO ASSERT → NO PROMOTION.
