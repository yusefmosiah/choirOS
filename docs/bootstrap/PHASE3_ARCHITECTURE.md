# ChoirOS Phase 3: Director + Associate Architecture

> Dual sandboxes. Ralph supervising Ralph. Vite lives in the Associate.

---

## Core Decisions

### 1. Dual Sandbox Model

Each user gets two sandboxes:

- Director sandbox: planning loop, policy, orchestration.
- Associate sandbox: ChoirOS UI + repo + tools.

The Director never edits files directly. All state changes are expressed as
Associate task types.

### 2. Vite in the Associate

The Associate runs the Vite dev server so the OS can rewrite itself live.
This is the vibecoding primitive.

### 3. Git Time Travel (v0)

Git checkpoints are the time travel mechanism. The Director requests git
actions as Associate tasks.

### 4. Control Plane Is Separate

Control plane code lives in a separate repo/folder and is not mounted into
Director or Associate sandboxes. It hosts a stable UI and spawns sandboxes.

---

## Architecture Diagram

```
┌───────────────────────────────────────────────────────────┐
│                      Control Plane UI                      │
│   (trusted, stable, spawns sandboxes, shows status)        │
└───────────────┬───────────────────────────────────────────┘
                │
                ▼
        ┌──────────────────────┐
        │   Director Sandbox   │
        │  (Ralph loop + LLM)  │
        └───────────┬──────────┘
                    │ DirectorTask
                    ▼
        ┌──────────────────────┐
        │  Associate Sandbox   │
        │ (Vite + repo + tools)│
        └───────────┬──────────┘
                    │ AssociateResult
                    ▼
                Git checkpoints
```

---

## Security Model (v0)

| Concern | Position |
|---------|----------|
| Prompt injection | Expected; Director verifies via Associate results |
| Session compromise | Handled at control plane later |
| Bad code edits | Git time travel + undo via Associate tasks |
| Secrets | Not inside sandboxes |

---

## Implementation Phases (v0)

| Phase | Goal | What to Build |
|-------|------|---------------|
| **3.1** | Dual sandboxes | Director + Associate spawn via Sprites |
| **3.2** | Vibecoding works | Vite in Associate + hot reload |
| **3.3** | Ralph loops | Director plans, Associate executes + verifies |
| **3.4** | Time travel | Git checkpoints + reset tasks |

---

*Updated: 2026-01-XX*
