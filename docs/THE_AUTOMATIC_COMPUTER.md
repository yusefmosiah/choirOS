# The Automatic Computer: A Position Paper

*From personal mainframe to global virtual brain*

---

## The Central Thesis: The Mainframe Returns

> **"The Model is the Kernel. The Chatbot is the CLI. The Automatic Computer is the Personal Mainframe."**

- **The Kernel (LLM)**: Raw, powerful, probabilistic processing. Handles the "compute" of intelligence. Like a kernel, it is hostile to direct human interaction.
- **The Shell (Chatbot)**: A text-based command line interface to the kernel. Synchronous, stateless, unscalable. Represents a regression in affordance ("Blank Screen Paralysis").
- **The Mainframe (Agentic OS)**: The missing layer. A persistence engine, window manager, and process scheduler that protects the user from the raw kernel and manages long-running tasks across all time scales.

This is not a new paradigm. It is the original paradigm—the UNIVAC's "Universal Automatic Computer"—returning as personal infrastructure rather than institutional bureaucracy.

---

## Abstract

The dominant AI interface paradigm—the chatbot—is wrong. Chatbots are synchronous: user speaks, AI responds, user waits. But useful AI work is asynchronous: research takes time, synthesis requires iteration, complex tasks unfold over hours or days.

We propose a different paradigm: the **automatic computer**. Not a chatbot you talk to. Not an app you use. A computational environment that observes your work, processes in the background, and responds through the same channels you already use—files, emails, notifications.

The automatic computer is **pansynchronous**: it operates across all time scales simultaneously. It is also **integrally connected** to the global virtual brain, drawing on collective knowledge while maintaining sovereign personal state. This is awkward to conceive abstractly but natural to experience: you write a note; later you find a critical review cross-referencing your entire context. You didn't invoke anything. The computer just... audited.

This paper outlines the paradigm, its technical architecture, and its business model.

---

## Part I: The Problem with Chatbots

### The Synchronous Trap

Chatbots demand attention. They create a conversational context that expects:
- User initiates
- AI responds
- User evaluates
- User continues or abandons

This is **synchronous** interaction. Both parties are present. The conversation has a beginning, middle, end. Context exists only within the session.

This works for simple queries. It fails for complex work:

| Task | Why chatbot fails |
|------|-------------------|
| Deep research | Takes hours, user can't wait |
| Multi-step projects | Context lost between sessions |
| Background monitoring | No trigger without user initiation |
| Collaborative work | Single-user, single-session model |

### The Attention Problem

Chatbots compete for foreground attention. But humans have limited foreground attention. We can only "talk to AI" for so many hours per day.

Meanwhile, background processing is unlimited. Your cloud storage syncs constantly. Your email receives messages while you sleep. Your calendar sends reminders without you asking.

The valuable AI is the AI that works while you don't.

### The Invocation Problem

Every chatbot interaction requires explicit invocation:
- Open the app
- Type the prompt
- Wait for response

This creates friction. More importantly, it requires the user to **know what to ask**. But often the most valuable help is help you didn't know to request.

Your dad accidentally hits a "rewrite" button. The AI mangles his email. He doesn't know ctrl-z. His original is gone.

This is the failure mode of explicit invocation: accidental triggers, unwanted transformations, destroyed trust.

---

## Part II: The Automatic Computer Paradigm

### Definition

An **automatic computer** is a computational environment that:
1. Observes user actions as an event stream
2. Processes in background without explicit invocation
3. Responds through existing channels (files, notifications, emails)
4. Maintains persistent state across sessions
5. Operates at all time scales (instant to indefinite)
6. **Performs continuous critical review of its own operation and context**

### Pansynchronous Computing

The automatic computer is **pansynchronous**—operating across all synchronicity modes:

| Mode | Time scale | Example |
|------|------------|---------|
| Synchronous | Instant | Autocomplete, inline suggestion |
| Near-sync | Seconds | File save triggers validation |
| Asynchronous | Minutes-hours | Research task runs in background |
| Persistent | Days-indefinite | Long-running monitoring, accumulating state |

This is conceptually awkward. A Turing machine operating at all time scales simultaneously is hard to visualize. But the **experience** is natural—especially when you can **see** the context through a mind map that visualizes the span of processes cycling through your workspace.

### The Action Stream

Instead of explicit invocation, the automatic computer observes:

```
ActionEvent {
  timestamp,
  action_type,    // "file_changed", "email_sent", "app_opened"
  target,         // what was acted upon
  context,        // surrounding state
}
```

Every user action emits an event. The automatic computer subscribes to this stream. It decides what's relevant. It processes in background. It responds when ready.

The user never "talks to AI." The user just uses their computer. The AI is infrastructure, not interface.

### The Response Channels

The automatic computer responds through channels the user already uses:

| Channel | Response type |
|---------|---------------|
| File system | New file appears, existing file updated |
| Email | Message in inbox |
| Notification | Alert on device |
| App state | UI reflects new information |

No new interface to learn. No chat window to monitor. The computer just becomes more helpful.

---

## Part III: The Killer App—Unilateral Auditor

The first application that validates the paradigm is not a chatbot or writing assistant. It is the **Unilateral Auditor**.

**Function**: Takes any input—text, topic, or user action—and produces a critical review cross-referencing the entirety of your world of context. It does not summarize. It *dissents*. It finds blind spots, contradictions, and uncited assumptions in your accumulated state.

**Execution**: Runs continuously in background. When you save a file, it checks against your historical claims. When you write a note, it cross-references your prior positions. When you research a topic, it surfaces what you've missed.

**Output**: A persistent audit log, queryable like any file. Not a conversation—an institutional memory with an immune system.

This is the anti-chatbot: instead of generating plausible continuations, it generates **critical friction**. It ensures your persistent compute volume doesn't become an echo chamber.

---

## Part IV: Technical Architecture

### The Personal Mainframe Model

We don't run agents locally (resource constraints, capability limits). We don't run agents in full isolation (no access to user context).

We **entangle** the user's machine with an automatic computer, creating a **personal mainframe** that leverages global compute while maintaining sovereign state:

```
User's Local Machine          Cloud Automatic Computer
├── Cloud storage sync   ←→   ├── SQLite workspace
├── File system              ├── Global model access
├── Email client         ←→   ├── Background agents
├── Notifications        ←    ├── Auditor process
└── Native apps              └── Mind map generator
```

The cloud storage drive is the entanglement point. User writes file locally → syncs to cloud → automatic computer sees event → processes → writes response → syncs back to user.

From user's perspective: the cloud folder became intelligent—and self-critical.

### SQLite as State Primitive

Agent state lives in SQLite:

```sql
CREATE TABLE workspace (
  id TEXT PRIMARY KEY,
  content BLOB,
  metadata JSON,
  updated_at TIMESTAMP
);

CREATE TABLE action_log (
  id TEXT PRIMARY KEY,
  action_type TEXT,
  target TEXT,
  context JSON,
  timestamp TIMESTAMP
);

CREATE TABLE agent_tasks (
  id TEXT PRIMARY KEY,
  status TEXT,  -- pending, running, complete
  input JSON,
  output JSON,
  created_at TIMESTAMP,
  completed_at TIMESTAMP
);
```

Single file. Portable. Queryable. Atomic transactions.

### S3 + Client-Side Encryption

```
S3 Bucket (shared)
├── {user_id}/{workspace_id}.sqlite.enc
└── ...
```

All users share infrastructure. Each user's data encrypted with their key. Platform cannot read user data. Users can export and own their workspace. The lock-in is mathematically impossible, creating trust.

### The Web UI as OS

The web interface presents an OS GUI:

```
Browser
└── choir.chat (or custom domain)
    └── OS GUI
        ├── Desktop with windows/panels
        ├── File browser (SQLite-backed)
        ├── Apps (research, writing, etc.)
        ├── Notifications
        ├── Mind map (active context span)
        └── Settings/permissions
```

Responsive: adapts to mobile, tablet, desktop. Same workspace, different rendering.

The "device" is not hardware. The device is the workspace, accessed from anywhere.

---

## Part V: The Permission Model

### Relationship-Based Access

Your automatic computer contains everything:
- Medical records
- Financial documents
- Work projects
- Personal notes
- Communication history

Different people should see different views:

```
Visitor → yourname.computer

Authentication determines access:
├── Spouse      → Full access
├── Doctor      → Medical records only
├── Colleague   → Work projects only
├── Client      → Portfolio, booking
└── Stranger    → Public bio, contact
```

Same workspace. Same data. Permissioned views.

### The Agent as Gatekeeper

When someone visits your automatic computer:

1. Agent identifies visitor (auth, stated relationship)
2. Agent determines access level
3. Agent presents appropriate view
4. Agent mediates interactions

Your agent represents you. It decides what to share, what to withhold, what to ask you about.

---

## Part VI: Business Model

### The Tiers

| Tier | Offering | Price |
|------|----------|-------|
| Free | choir.chat/{username} | $0 |
| Pro | Custom domain (you.computer) | $X/mo |
| Team | Shared workspace, permissions | $Y/seat/mo |
| White-label | Fully branded, their infrastructure | Enterprise |

### Custom Domains as Identity

Your automatic computer becomes your online identity:

```
alice.computer
drsmith.health
acme.internal
```

Business card of the future:
```
┌─────────────────────────┐
│  Alice Chen             │
│  alice.computer         │
│  [QR code]              │
└─────────────────────────┘
```

Scan → interact with Alice's agent → see what she's shared → request access.

The workspace *is* the presence. Not a profile. Not a portfolio. A living environment. The domain is a human-readable pointer to your public key.

### White-Label Distribution

Businesses want their own automatic computer:

```
smithlaw.legal
├── Their branding
├── Their auditor
├── Their client permissions
└── Choir infrastructure (invisible)
```

They pay for infrastructure. They own the customer relationship. Choir is the platform layer.

### The App Ecosystem—Hyper-Exponential Composition

The app ecosystem is not a planned feature. It is an **emergent property** of vibecoding with live reload.

**Reality**: Building apps is pure prompt-to-executable. Models improve continuously. Component libraries compound. This is **hyper-exponential growth**: each app makes the next easier to build.

**Composition**: Agents spawn child agents as apps. SQLite is the IPC layer. The citation graph is the composition graph.

**Moat**: Not the apps themselves, but the **speed of composition**. By the time competitors replicate the infrastructure, the ecosystem has moved exponentially forward.

### The Citation Graph

When alice.computer cites bob.computer:
- Citation link (knowledge graph)
- Social connection (people graph)
- Payment flow (economic graph)

Attribution is connection. The citation graph *is* the social graph.

---

## Part VII: The Platform Moat

### What's Not a Moat

- **AI capability**: Commodity, everyone has access to same models
- **Chat interface**: Everyone has one
- **Text generation**: Table stakes, embedded everywhere

### What Is a Moat

- **Citation graph**: Deepens with every use, network effects
- **Permission model**: Encodes relationships, hard to rebuild elsewhere
- **App ecosystem**: Developers build for the platform, users expect the apps
- **Custom domains**: Identity tied to platform
- **Data portability**: Paradoxically, no lock-in creates loyalty (trust)

### The Distribution Flywheel

1. User creates workspace
2. User shares workspace URL (bio, business card, email signature)
3. Visitor experiences workspace
4. Visitor wants their own
5. Visitor signs up
6. Repeat

Every workspace is marketing. Every user is distribution.

---

## Part VIII: Why Now

### The Capability Overhang

Current models can do far more than current interfaces expose. The constraint is not AI capability. The constraint is:
- Context engineering
- Integration architecture
- UX paradigm

The chatbot interface wastes model capability on synchronous Q&A. The automatic computer unlocks capability for **continuous critical work**.

### The Infrastructure Convergence

All pieces now exist:
- Models capable of complex reasoning and action
- Cloud storage ubiquitous and cheap
- SQLite proven at scale
- S3-compatible storage everywhere
- Encryption well-understood
- Web technologies capable of OS-like UI

No new technology required. Just assembly.

### The Trust Crisis

AI-generated content floods the internet. Provenance is lost. Attribution is broken. "Who said this?" becomes unanswerable.

The Unilateral Auditor and citation graph solve this: **provenance through persistent, self-critical computation**.

---

## Part IX: Strategic Position

### "Short AGI, Long Agency"

The bet that underlies this project:

- **Hard Domains (Code, Logic, Math)**: Fall inside the "Convex Hull" of training data. AI progress here will be super-exponential.
- **Soft Domains (Bio, Novelty, High Art)**: Fall outside the hull. Progress flattens due to lack of training data or systemic complexity.

We don't need AGI (Digital God) to build the Automatic Computer. We only need Reliable Reasoning (Digital Labor).

### The Industrial Frame

To cut through AGI hype/fear, we reject the **Biological Metaphor** and embrace the **Industrial Metaphor**:

| Feature | AGI Narrative | Agentic Narrative |
|:--------|:--------------|:------------------|
| **Metaphor** | Biology (Brain/Neuron) | Industry (Factory/Loom) |
| **Role** | Rival / Replacement | Infrastructure / Staff |
| **Dynamic** | Dialogue (Chatting) | Delegation (Dispatching) |
| **Promise** | "It knows everything." | "It does the work." |

**Key Copy**:
- *"The Model is the Kernel; the Chatbot is the Shell."*
- *"From software you operate to software that operates—and audits itself."*
- *"Don't rent a brain. Build a mainframe."*

---

## Part X: The Vision—Global Virtual Brain

Your automatic computer is not isolated. It is **integrally connected** to the global virtual brain—the sum of all models, knowledge, and agents. Your personal mainframe:
- Draws on collective intelligence
- Maintains sovereign personal state
- Contributes back through citations and audits

This is not decentralization. It is **sovereign participation** in a global computational organism.

---

## Conclusion

The chatbot was a detour. The automatic computer corrects this. It is:

- **Pansynchronous**: Operates at all time scales
- **Observable**: Watches user actions, not demands
- **Responsive**: Replies through existing channels
- **Persistent**: Maintains state indefinitely
- **Permissioned**: Shows different views to different relationships
- **Portable**: User owns their data, can leave anytime
- **Distributable**: White-label, custom domains, app ecosystem
- **Self-Critical**: Continuous audit ensures intellectual hygiene
- **Connected**: Integral node in the global virtual brain

The interface is not conversation. The interface is the environment itself—files, notifications, apps, the desktop, the mind map. The AI is not a participant in your work. The AI is the infrastructure your work runs on.

This is the automatic computer. This is Choir.

---

*January 2026*
