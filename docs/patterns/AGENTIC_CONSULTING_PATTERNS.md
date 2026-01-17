# Agentic Consulting Patterns: Asking Less, Researching More

This document captures a set of interaction and control-loop patterns for agentic systems that must operate with users who often cannot answer deep technical questions. The goal is to maintain forward progress, reduce user burden, and improve outcome quality by using research, defaults, and verifiers—while escalating only when user preference or risk genuinely requires it.

## 1) How to categorize the pattern

This is primarily **agent strategy and tactics** (control policy), expressed through **consulting best practices** (decision framing and evidence-backed recommendations). “Bedside manner” is the surface manifestation (how it sounds), but the substance is an operating model:

- **Strategy / Tactics:** Decide when to ask, when to research, when to assume defaults, when to split work, when to escalate.
- **Consulting Best Practices:** Provide options with trade-offs, recommend a default, document assumptions, and keep a clear decision record.
- **Bedside Manner:** Ask fewer, better questions; avoid making users feel inadequate; keep the system’s posture confident but reversible.

## 2) The core failure mode

Many coding agents ask users questions that the context indicates the user is unlikely to answer, e.g., “Which auth strategy?” or “What architecture do you want?” The predictable response is “idk, what do you think?”—which means the agent has offloaded ambiguity instead of resolving it.

This creates thrash:
- Users are blocked by questions they can’t answer.
- The agent loses momentum and starts planning without evidence.
- The system converges to stubs, generic “best practices,” or vague timelines.

## 3) The director’s role: risk manager + scheduler

The director should behave like a risk manager:
- Convert ambiguity into **observable evidence** (verifiers, demos, receipts).
- Limit blast radius (budgets, sandboxes, capabilities).
- Sequence work to burn down uncertainty early (spiral/rotational passes).

Question asking is a tool of last resort, not a default behavior.

## 4) Ask vs Research: a decision policy

### 4.1 Three classes of questions

A) **Preference questions** (user must decide)  
Examples: naming, tone, UX feel, brand voice, trade-offs where values dominate.

B) **Risk / policy questions** (must escalate)  
Examples: security posture, privacy retention, compliance constraints, money movement, irreversible migrations.

C) **Researchable ambiguity** (agent should resolve)  
Examples: library choice, API semantics, deployment patterns, “what is best practice here,” performance constraints.

Default behaviors:
- **A:** propose a default + quick override; only ask if it materially changes output.
- **B:** apply conservative policy and/or require explicit approval (human 2FA in higher-stakes systems).
- **C:** spawn research subagents and decide, recording rationale.

### 4.2 A simple decision rule

For any ambiguity, the director estimates:

- **Answerability:** Can repo/docs/web evidence resolve this?
- **Impact:** What’s the downside if wrong?
- **Reversibility:** How expensive is changing later?
- **User-likelihood:** Is the user likely to know or care?

If answerability is high and user-likelihood is low → **Research and decide**.  
If impact is high → **Research + conservative default + escalate threshold**.  
If it is preference-sensitive → **Default + ask narrowly**.

## 5) The “default + evidence + escape hatch” pattern

Instead of asking:
- “What should we use for X?”

Do:
1) Recommend a default.
2) Provide brief trade-offs.
3) State what would change the recommendation.
4) Provide an escape hatch: “If you prefer Y, say so.”

Template:
- “I will default to **X** because it fits constraints **A/B** and matches common practice in **C**. The main trade-off is **T**. If your priority is **P**, we should choose **Y** instead. I can switch later with cost **K**.”

This keeps forward progress while respecting user agency.

## 6) Liberal research subagents with cost controls

Research should be liberal but bounded, using:
- Small, specialized retrieval agents (cheap models).
- Strict budgets (max sources/pages/time).
- Typed outputs (decision record + citations), not long prose.
- Caching via “skills” / “best-practice packs” for common questions.

Cost-control knobs:
- Model tier selection (cheap for retrieval, stronger for synthesis only if needed).
- Parallelization (multiple narrow retrievals) vs. one broad scrape.
- Evidence set hashing and reuse (avoid repeated crawling for the same question).

## 7) Spiral (rotational) passes: how the director keeps momentum

The director should plan in “passes” that rotate the work mode around an invariant axis (objective/risk). Each pass must produce an intermediate verifiable result. Typical mode rotation:

- **Build:** smallest end-to-end “walking skeleton”
- **Verify:** add/strengthen objective checks, replay, determinism
- **Harden:** policy gates, sandboxing, negative tests, anomaly detection
- **Expand:** broaden scope only after signals are green

A plan that is merely “Stage 1 build X, Stage 2 build Y” is not a spiral; it’s linear decomposition.

## 8) High-value clarifying question: the 30-second demo

When user input is genuinely needed, ask the one question that collapses ambiguity:

- “What would you consider a simple successful demo—something you can verify in 30 seconds? What do you do, and what do you expect to see?”

Even non-experts can answer this. The director then derives:
- Pass 1: make the demo true
- Verifier: script that reproduces demo
- Risks: what could block demo
- Next passes: verify/harden/expand

## 9) Verifiers that force the right behavior

To condition agents toward spiral behavior and away from stubs:

Plan lints (fail the plan if):
- Pass 1 lacks a demo script and objective verifiers.
- More than 2 passes are fully specified (signals overplanning).
- The plan contains calendar timelines (weeks/months/sprints).
- Passes are component lists rather than vertical slices.

Execution gates:
- Anti-stub gate (no TODO/NotImplemented/mock returns in touched files).
- “No new interface without an integration test crossing it.”
- Diff budget caps (max files/lines).
- End-to-end demo command must succeed.

Telemetry-driven replanning:
- If progress is non-monotonic for N iterations → split the work item or change strategy before escalating model tier.

## 10) “Bedside manner” guidelines (surface behavior)

The system should sound like a competent consultant:
- Avoid making the user feel responsible for technical unknowns.
- Ask fewer questions; ask only those that materially change outcomes.
- Make assumptions explicit and reversible.
- Be decisive, but humble about uncertainty (calibrated confidence).
- Use short decision packets, not long interrogations.

Bad:
- “What architecture do you want?”
Good:
- “Defaulting to X; here is why; here is when we’d choose Y.”

## 11) Additional patterns in the same vein

A) **Assumption ledger**  
Maintain a short, versioned list of assumptions the system is operating under. Update only when evidence changes.

B) **Decision records (mini-ADRs)**  
Every nontrivial design choice produces a 5–10 line ADR: context, decision, alternatives, consequences, verifiers.

C) **Escalation ladder**  
Cheap model → stronger model → adversarial reviewer agent → human approval (only for high-impact/risk).

D) **Quarantine then promote**  
Outputs go to a quarantine index first; promotion requires verifier attestations and (optionally) challenge windows.

E) **Evidence-first planning**  
Before implementation, the director runs a bounded discovery pass: repo map, relevant constraints, candidate approaches.

F) **Counter-case requirement**  
For important decisions, spawn a critic subagent to produce the best opposing argument and missing sources.

G) **Receipts everywhere**  
Every action emits a receipt: what context was used, what verifiers ran, what changed, and why.

## 12) Practical adoption: where to put this

These patterns should be enforced at three levels:
- **System prompt constitution (director/associate)**
- **Plan schema + lints**
- **Runtime gates + telemetry**

If enforced mechanically, agents “learn” spiral behavior because it is the only path that passes checks and keeps budgets intact.
