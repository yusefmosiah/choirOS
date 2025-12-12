# The Evolution of Choir: From Yield Farming to the Agentic Computer

_A narrative of transitions — December 2025_

---

## Part I: The Stellar Hackathon Origin

Tuxedo began as something else entirely: a yield farming agent for the Stellar blockchain, built for a hackathon using the Stellar Scaffold framework.

The premise was narrow and practical: use AI to optimize DeFi yield strategies. An agent that watches markets, identifies opportunities, executes trades. The blockchain was Stellar. The tooling was DeFindex. The goal was to win a hackathon by building something useful in a specific vertical.

This is where many AI projects start—with a concrete, bounded problem. Yield farming optimization. Legal document review. Customer support automation. The instinct is understandable: pick a lane, go deep, demonstrate value in a measurable domain.

But something was wrong with the fit.

---

## Part II: The Pivot Back to Choir

The project kept drifting back toward Choir—the long-running vision that had been evolving since 2015 through many names: Phase4, Bluem, Blocstar, ChoirGPT, and others. The core idea persisted through all iterations: a system for collective intelligence with proper attribution and incentives.

Why couldn't the yield farming agent stay a yield farming agent?

Because the Choir vision was always pulling at the architecture. Citation graphs. Knowledge provenance. Economic incentives for quality contributions. Multi-agent orchestration. These concepts kept appearing in the design documents, kept expanding the scope beyond "yield optimization" into something more fundamental.

The yield farming agent was a costume. Choir was the body underneath.

---

## Part III: The Context Engineering Revelation

The pivotal realization came through struggling with agent architecture: **narrow agents don't scale because they lack their own environment**.

A yield farming agent needs to:

- Research market conditions
- Analyze smart contracts
- Backtest strategies
- Execute transactions
- Monitor outcomes
- Learn from results

A ghostwriting agent needs to:

- Research source material
- Analyze existing literature
- Draft content
- Verify citations
- Revise based on feedback
- Learn from acceptance/rejection

Different domains. Same underlying capabilities: research, analysis, synthesis, execution, learning.

The revelation: **a narrow agent specialized for yield farming is isomorphic to a general agent with a yield farming context.** The difference isn't the agent—it's the workspace the agent operates in.

This is context engineering: instead of training specialized models, you provide general models with specialized context. The prompt, the tools, the files, the history—these create the specialization at runtime rather than training time.

The implication is profound: **you don't need N specialized agents for N domains. You need one capable agent and N well-designed workspaces.**

---

## Part IV: The Architecture Exploration

With this insight, the project entered an exploration phase. If narrow agents become general agents in specialized workspaces, what architecture supports this?

The journey passed through multiple stacks:

**LangGraph era**: Graph-based workflow orchestration. Nodes as processing steps, edges as control flow. Powerful but rigid—the graph structure itself became a constraint.

**MCP (Model Context Protocol) era**: Service-oriented architecture where each phase runs as a separate server. More modular, but added complexity without proportional benefit.

**Qdrant-Sui MVP era**: Focus on the data layer—vector search for semantic memory, blockchain for economic primitives. The right building blocks, but the agent-environment relationship still wasn't clear.

**Conductor + Agents era**: Client-side orchestration with server-side specialized agents. Getting closer—the split between orchestration and execution started to clarify.

Through all these iterations, a pattern emerged: the architecture kept evolving toward **separation of the agent from its environment**. The agent is the capability. The environment is the context. The interface between them is the action stream.

---

## Part V: The Agentic Computer Thesis

The synthesis arrived: **the computer itself should be the agent's environment.**

Not a chatbot you talk to. Not an API you call. A complete computational environment—file system, applications, notifications, network—that agents can observe and operate.

This reframing changes everything:

| Old framing        | New framing              |
| ------------------ | ------------------------ |
| Agent as tool      | Agent as operator        |
| User invokes agent | Agent observes user      |
| Synchronous chat   | Pansynchronous operation |
| Context as prompt  | Context as environment   |
| Output as response | Output as file/action    |

The agentic computer is:

- **Pansynchronous**: Operates at all timescales, from instant autocomplete to long-running background research
- **Observable**: Agents watch file changes, app events, user actions—not just explicit invocations
- **Responsive through existing channels**: Files appear, emails arrive, notifications surface—no new interface to learn
- **Persistent**: State survives sessions, builds over time, learns from history

The user doesn't "talk to AI." The user works in an environment that happens to be intelligent.

---

## Part VI: The Human Experience Design Turn

With the agentic computer thesis in hand, the question became: what should this actually look like?

The answer emerged through thinking about human experience, not just technical architecture. How do people actually use computers? What interfaces are already intuitive?

The desktop metaphor—files, folders, windows, notifications—has been the dominant computing paradigm for 40 years. People understand it. It works on every device. It's been refined by trillions of user-hours.

The insight: **don't invent a new interface. Make the familiar interface intelligent.**

A web-based desktop environment where:

- Files behave normally, but agents can read and write them
- Applications work as expected, but agents can operate them
- Settings are configurable, but agents can modify them via prompts
- The experience is familiar, but the substrate is intelligent

This led to the "vibe-design" concept: the first interaction with the agentic computer is customizing it through natural language. User arrives → describes ideal workspace → agent modifies theme files → desktop transforms.

This is the teaching moment: "I prompted → the computer changed." Sets the expectation for all future interaction.

---

## Part VII: The DaedalOS Decision (and Its Reversal)

Evaluation of browser-based desktop environments initially led to DaedalOS as the foundation:

**Why DaedalOS seemed right:**

- **Mobile responsiveness**: Works fast on phones and tablets
- **MIT license**: Maximum freedom for forking and modification
- **Rich existing foundation**: File system, terminal, text editors, WebLLM, browser—all working

**What changed:**

After cloning the codebase and analyzing it more deeply, the fundamental architecture didn't match our needs:

- **Local-first vs distributed**: DaedalOS is built around BrowserFS/IndexedDB for local storage. ChoirOS needs a global distributed system—per-user SQLite synced to S3, NATS event bus, cloud agents.
- **Skeuomorphic baggage**: DaedalOS faithfully recreates Windows. We want something radically different—not a local OS but a global system that *appears* local.
- **Complexity overhead**: Games, emulators, and hundreds of components to remove. The 80/20 is clearer when building fresh.
- **Auth and multitenancy**: Fundamental additions that touch every layer—easier to design in from scratch than retrofit.

The revised decision: **Build the 80/20 from scratch.** Use daedalOS code as reference material for window management patterns, but architect something fundamentally different:

- **NATS JetStream** as the event bus / kernel
- **Firecracker microVMs** for isolated agent execution
- **Per-user SQLite** synced to S3 (sovereignty + portability)
- **Qdrant** for vector search
- **Vite + React + TypeScript** (not Next.js)
- **TipTap** for writing (not Monaco—user-facing names like "Writer", not library names)

---

## Part VIII: What Carries Forward

The Tuxedo codebase—born as a yield farming agent, evolved through multiple architectural iterations—has served its purpose. It was the crucible where these ideas crystallized.

What carries forward to choirOS:

**From Choir's long history:**

- Citation graph and attribution
- Deposit economics (stake behind claims)
- Novelty and citation rewards
- CHOIR token on Sui mainnet

**From Tuxedo's architecture exploration:**

- Context engineering principles
- File-as-memory pattern
- Pansynchronous operation model
- Action stream concept
- Passkey authentication (to be integrated)

**From daedalOS (as reference, not fork):**

- Window management patterns
- Desktop metaphor UX principles
- Proof that web desktops can be fast

**What's new in the synthesis:**

- NATS-based global log stream
- Firecracker microVMs for agent isolation
- Per-user SQLite + S3 state architecture
- Vibe-design as onboarding
- Relationship-based permissions
- Custom domains as identity (alice.computer)

---

## Conclusion: The Paradigm Revealed

The yield farming agent couldn't stay a yield farming agent because the underlying paradigm wanted to emerge.

Narrow agents are inefficient—they duplicate capabilities across domains. General agents with specialized workspaces are the correct architecture. Those workspaces should be complete computational environments. Those environments should be the web desktop paradigm, made intelligent.

The chatbot was a detour. The agentic computer is the destination.

Choir has been reaching toward this from the beginning—through all the names, all the pivots, all the partial implementations. The technology finally caught up to the vision. The vision finally found its form.

choirOS is where the journey continues.

---

_December 2025_
