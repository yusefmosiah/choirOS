
# Choir Agentic Desktop – Architecture, UX, and Wedge Use Case
**Date:** December 11, 2025

This document synthesizes the current thinking around Choir as an *automatic computer* with a desktop UX and citation-based economics.

---

## 1. Big Picture: From Web3 and Chatbots to an Automatic Computer

### 1.1 Web3 is dead without AI

The original Web3 vision (read–write–own, decentralized social, wallets as identity) assumed:
- A **human** as the primary actor.
- A **wallet** as the core primitive.
- “Ownership” = signing with a key in a browser and writing to a chain.

In an AI-native world:
- Wallets are just **files and key material**.
- An AI agent will manage **many wallets on many chains**, under policy.
- The user interacts with **projects, policies, and artifacts**, not chains or wallets.

So:
- Web3 social (Farcaster, Lens, etc.) = *Twitter clones on-chain*, no 10x UX, no deep new primitive.
- Web3 without AI is a mis-specified future.
- The real story is: **AI + crypto + media + governance** fusing into a single operating layer for the 21st century.

### 1.2 Finance, media, and narrative power

The deep reality:
- **Credit** (capital) and **credibility** (attention/trust) are tightly coupled.
- Milken’s letters and Ackman’s decks/tweets show that narrative itself is a *funding instrument*.
- In modern markets, media is not “about” finance; media **is a financial tool**.

Polymarket shows a degenerate version of this:
- Price is the real object; comments are cheap talk / entertainment.
- Social layer is mostly low-effort noise because it has no structured consequences.

Choir’s ambition:
- Turn **speech and priors themselves** into financially meaningful objects:
  - Priors and artifacts are cited by agents.
  - Citations trigger economic flows.
  - Words become programmable financial instruments with attribution and scoring.

---

## 2. Why Chatbots Aren’t Enough

### 2.1 Stale threads and opaque memory

Current assistant UX problems:
- Chat threads accumulate **stale state** and are bad as long-term memory.
- “Memory” features are opaque, out-of-date, and vendor-siloed.
- Export is a multi‑MB JSON blob—technically “portable,” practically useless.

This is acceptable for casual Q&A, but totally inadequate for serious work.

### 2.2 Deep reasoning is inherently slow

Real “deep reasoning” requires:
- Multiple sequential queries and tool calls.
- Reading, comparing, and transforming many artifacts and sources.
- Non-trivial planning, not single-shot responses.

There is no magic “instant deep reasoning.” Either:
- You hallucinate fast, or
- You **precompute** expensive reasoning and **cache** it for reuse.

Caching is the only honest way to make deep answers feel instant.

### 2.3 Why caching forces social and economic design

If deep reasoning is cached and reused, you must answer:
- Who owns the artifact that’s being reused?
- Who is allowed to see/use it (privacy and access control)?
- Who gets paid or credited when it’s reused?

So:
- A real “memory moat” cannot just be a vendor’s internal cache.
- Memory must become a **user- and network-owned asset**, with:
  - explicit structure (artifacts, logs, prefs)
  - simple import/export (e.g. SQLite/zip)
  - attribution and economics (citation rewards).

For an **automatic computer**, JSON dumps are obviously hostile; the OS must treat user state as a portable, legible dataset.

---

## 3. Automatic Computer Architecture

### 3.1 Local shell, remote brain

Core principle:
> **Local-feeling shell, remote brain and body.**

- **Local (browser or native app):**
  - Desktop UI (background, icons, windows).
  - Window manager: open/minimize/drag/resize.
  - Local cache of artifacts’ *last known state* for instant rendering.
  - Zero dependence on the network for basic interactions.

- **Remote (cluster):**
  - Agents with tools in **sandboxed microVMs/containers**.
  - Databases and vector stores for artifacts and logs.
  - Log streaming middleware (NATS / JetStream) as the central event spine.
  - Optional GPU-backed models and infra.

The user’s “computer” is a **thin client** over a distributed system that *behaves* like one PC.

### 3.2 Remote sandbox: agents don’t touch your real machine

Agents require:
- Full “computer use” (filesystem, network, tools) **inside** a sandbox.
- Strict isolation from the user’s actual device.

Design:
- Each agent (or session) gets a **remote microVM**:
  - Linux userland, shell, runtime (Python/R/…).
  - Limited APIs and credentials (wallets, HTTP, S3, etc.).
- Agent reads/writes artifacts via API, not by touching the user’s local disk.
- If the agent is misused, injected, or misaligned, it can only damage its VM.

Your laptop = sacred.
Remote VM = disposable body for agents.

### 3.3 Log streaming middleware as the kernel bus

NATS/JetStream-style stream is the **spine** of Choir:

Every meaningful event is logged:
- User actions:
  - `UserAction.CreatedArtifact`
  - `UserAction.EditedSpec`
  - `UserAction.CommandIssued (?new, ?publish, etc.)`
- Agent activities:
  - `Agent.RunStarted`
  - `Agent.CitedPrior {prior_ids: [...]}`
  - `Agent.RunCompleted`
- Economics:
  - `Economics.RewardAssigned`
  - `Economics.SplitUpdated`

This gives:
- A single source of truth.
- Replay capability (recompute rewards or metrics from genesis).
- Natural “social” views (feeds, timelines) as just **filtered views on the log**.
- Easy addition of new agents as **log subscribers** (background workers).

### 3.4 Citation economics pipeline

1. An agent generates an output.
2. It emits `Agent.CitedPrior` events with IDs and weights for the priors it used.
3. An economics service subscribes, computes reward allocations, and emits `Economics.RewardAssigned` events.
4. Token rewards (or balances) are updated accordingly.

This is asynchronous and decoupled:
- Agents don’t need to know token math.
- UI just renders balances and stats.
- Economics logic can change and be replayed later.

---

## 4. Desktop UX Paradigm

### 4.1 Web desktop in the zeitgeist

The OpenAI merch site and similar interfaces show:
- A **web desktop** aesthetic: grids of icons, floating windows, subtle drag affordances.
- Cultural readiness for “desktop-in-browser” as a normal interface, not a gimmick.

This validates using a desktop metaphor in 2025:
- Users already understand icons, windows, and taskbars.
- You can focus your novelty on the **substance** (agents, artifacts, economics), not on teaching basic navigation.

### 4.2 Choir desktop: differences from kitsch web-desktops

Most “web desktops” today:
- Are skins over simple web flows (e-commerce, portfolios, etc.).
- Fake windows and icons; under the hood they’re just monolithic apps.

Choir’s desktop:
- Is a **thin shell** over:
  - a distributed agent cluster,
  - a log spine,
  - an artifact graph,
  - and an economic layer.
- Icons represent:
  - regions of semantic space,
  - plus their artifact history,
  - plus ownership and reward flows.

So it looks familiar but actually fronts an entire programmable “social OS.”

### 4.3 The `?` paradigm: Start menu + console + chat

In the desktop UI, the bottom bar looks like:

`[ ? ] [ ________________________________ ]`

- Left: **`?` button** (Start / command menu).
- Right: **global input** (command + question bar).

Behavior:

- Clicking `?` opens a **command palette** with buttons:
  - “New artifact” → pre-fills `?new artifact "Untitled"`
  - “New project” → `?new project "..."`
  - “Open artifact…” → `?open ""`
  - “Publish” → `?publish`
  - “Status” → `?status`
  - “Help” → `?help`
  - “Clear context” → `?clear`

- Tapping a button:
  - closes the menu,
  - autopopulates the text input with the corresponding command,
  - focuses the input so the user sees the **equivalence** between clicking and typing.

- Typing without `?` (e.g. “Summarize this and tighten the intro”) = natural language **query**, scoped to current focus (e.g. active artifact window).

This is the “threadless” conversational layer:
- There are no multiple chat threads.
- There is **one global console** that always acts on the current workspace / artifacts.

### 4.4 Threadless state: artifacts, not transcripts

State is not stored in chat logs. Instead:
- **Artifacts** (docs, specs, boards, reports) hold the long-lived state.
- **The event log** records how they were formed and updated.
- The `?` bar simply issues intents that mutate artifacts and spawn agent runs.

Example:
- Focus: “Acme Bio Trial Plan” artifact window is open.
- User input: “Update this with the new trial start date and today’s safety findings.”
- System:
  - Logs `UserAction.ChatUtterance` with focused artifact ID.
  - Agent reads the artifact + relevant logs.
  - Writes a new version of the artifact and emits `Artifact.Updated` + `Agent.CitedPrior`.
  - The desktop shows the updated artifact and a short inline message:
    “Updated ‘Acme Bio Trial Plan’ with new timeline and safety notes.”

The “conversation” is ephemeral; the artifact and log are the memory.

---

## 5. Memory, Portability, and Fairness

### 5.1 Current lab memory vs what people deserve

Today’s lab assistants:
- Store memory as opaque, vendor-managed profiles.
- Allow export only as giant JSON chat dumps.
- Treat memory as a **lock-in moat**, not a user asset.

In an **automatic computer**, the logical design is:
- Memory = artifacts + event log + preferences, with clear schemas.
- Import/export = **simple, structured bundles** (e.g. SQLite DB + zip of attachments).
- Users can:
  - download their “computer state”,
  - move it to another host,
  - or run it against another model provider.

This breaks “memory as hostage” and replaces it with “memory as user-owned capital.”

### 5.2 Memory as cache + social substrate

Because deep reasoning is expensive, and caching is essential, a social/economic structure is needed to make caching fair and safe:
- Access control (private, group, public, licensed).
- Attribution (who wrote which prior? who edited it?).
- Rewards (who gets paid when an artifact is reused in agent reasoning).

Choir’s citation log and economics engine are designed to:
- treat the global cache of thought as a **public good with private claims**.
- pay contributors when their artifacts become part of the hot path.

---

## 6. Serious Use vs “Normie” Use

### 6.1 Scientific / professional use: bioinformatics archetype

For bioinformatics and similar fields, users need:
- A **persistent distributed filesystem** (data, scripts, configs, outputs).
- Sandboxed agents with **full computer use** (tools, pipelines, environments).
- Artifact-based reports, not transient chat.
- Reproducibility, auditability, and rerunnable workflows.

Agentic desktop is non-negotiable here:
- Chatbots with stale threads and no filesystem simply cannot handle the workload.

---

## 7. Moats and Ecosystem Dynamics

### 7.1 Why traditional B2B / VC lenses can’t see this

Most crypto VCs and B2B-focused investors:
- Think in terms of:
  - enterprise SaaS,
  - APIs,
  - dashboards,
  - B2B cost savings.
- Dismiss “social + tokens + OS-like agent layers” as messy, too consumer, or too early.

They’re structurally blind to:
- a consumer-grade **agentic OS**,
- with an embedded **citation economy**,
- forming a new medium for public and semi-public thought.

### 7.2 Why labs will rediscover parts of this but can’t clone it fully

Labs (OpenAI, Google, Anthropic, xAI, Perplexity, etc.) are on a collision course with:
- **Agentic workspaces** (Projects, Canvas, Workflows).
- **Global context** (cross-device memory, “operating system” behavior).
- **Citations / provenance** (due to training-data and IP pressures).

They will almost inevitably implement:
- some form of automatic computer,
- some form of global workspace,
- some form of attribution / citation UI.

Where they are constrained:
- They can’t credibly issue and govern **neutral, user-owned economics**.
- They are bound by:
  - ad or SaaS business models,
  - shareholder expectations,
  - regulatory and IP optics.

They can copy the **UX and some of the plumbing**, but not the full **economic & governance layer** without massive internal contradictions.

### 7.3 Realistic moat for Choir

The defensible pieces are:
1. **Mechanism design from genesis**
   - Transparent, dominant-strategy-friendly citation rewards.
   - Token flows tied directly to the log and artifacts.
   - Fair splits between authors, editors, and citers.

2. **Neutral substrate and credible commitments**
   - Not owned by a single AI lab.
   - Designed so users see their work as **permanent capital**, not exhaust.

3. **Data gravity + habit**
   - Once users’ thoughts, research, and economic claims live in this OS, the cost of leaving is not purely technical, it’s cognitive and financial.
   - Export must be easy, but the *ecosystem value* is hard to replicate.

4. **Culture and selection effects**
   - Attract people who care about:
     - better discourse,
     - ownership of their cognition,
     - and sane economic alignment.
   - That community composition is itself part of the moat.

---

## 8. Summary

- Web3 social and prediction-market “social” are dead-ends for serious discourse.
- A real **21st‑century medium** must integrate:
  - AI agents,
  - crypto rails,
  - media/artifacts,
  - and governance/economics.
- Chatbots are useful interfaces but terrible foundations for serious, persistent work.
- The right foundation is an **automatic computer**:
  - local desktop UX,
  - remote sandboxed agents,
  - log streaming middleware,
  - artifact-centric state,
  - and portable memory.
- Choir’s twist is to make:
  - the **global cache of thought** a user‑owned, rewarded substrate, and
  - the **desktop UX** the natural way to inhabit that substrate.

This is the current snapshot of the Choir agentic desktop vision and its surrounding strategy.
