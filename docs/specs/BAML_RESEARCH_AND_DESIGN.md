# BAML Research & Design: The Type-Safe Foundation

**Status:** DRAFT
**Date:** 2026-01-18
**Scope:** Deep integration of BAML (Boundary AI Markup Language) across ChoirOS.

## Executive Summary: The Acceleration Thesis

We are currently transitioning from **Spiral 2 (Web Desktop)** to **Spiral 3 (Verification & Gates)**.

The primary friction in Spiral 3 is "epistemic glue": asking an LLM to look at a file and say "Pass/Fail" with a reason requires parsing, validation, and retry logic. Doing this with raw strings and `json.loads` is creating technical debt at the exact moment we need velocity.

**Thesis:** Adopting BAML now is not a distraction; it is an **accelerator**.
1.  **Eliminates "String Parsing Hell":** Verifiers become typed functions returning `VerifierOutcome` objects.
2.  **Enables "Moods" for free:** BAML’s client abstractions (Fallbacks, Retries, Round-robins) map 1:1 to ChoirOS Moods (CALM, CURIOUS, SKEPTICAL) without writing custom router logic.
3.  **Solves the Streaming Problem:** We need real-time UI updates (E4 Register). BAML streaming provides guaranteed partial types, allowing the UI to render "Thinking..." states safely.

---

## 1. Architecture: BAML "Everywhere"

We replace the concept of "Prompts" with "Functions" and "Models" with "Clients".

```mermaid
graph TD
    subgraph "Host (Supervisor)"
        Orchestrator[Run Orchestrator]
        BAML[BAML Client]
        EventStore[AHDB / Event Store]
    end

    subgraph "BAML Layer (.baml)"
        Schemas[Type Definitions]
        Funcs[LLM Functions]
        Clients[Client Strategies (Moods)]
    end

    subgraph "Model Provider"
        OpenAI
        Anthropic
        Local[Ollama/Local]
    end

    Orchestrator -->|Call Typed Func| BAML
    BAML -->|Generate Prompt| Clients
    Clients -->|API Request| OpenAI
    Clients -->|API Request| Anthropic
    Clients -->|Retry/Fallback| Clients
    BAML -->|Stream Partial Typed Objects| EventStore
```

### 1.1 Model Abstraction via Moods
We verify *capabilities*, not models. ChoirOS defines "Moods" which BAML implements as Client Strategies.

| Choir Mood | Behavior | BAML Client Strategy |
|------------|----------|----------------------|
| **CALM** (Default) | Fast, cheap, forgiving. | `fallback(GPT-4o-mini, Claude-3-Haiku)` |
| **CURIOUS** (Research) | High temp, broad context. | `round_robin(Gemini-1.5-Pro, Claude-3.5-Sonnet)` |
| **SKEPTICAL** (Verify) | Low temp, reasoning-heavy. | `fallback(Claude-3.5-Sonnet, GPT-4o)` + `retry_policy(max=3)` |

**Implementation:**
In `.baml` files, we define these strategies explicitly. The Python code simply asks for the function behavior it needs, or BAML functions can be parameterized by client if dynamic switching is needed (or we organize functions by capability).

### 1.2 Verification Threads (Spiral 3)
Verifiers are the "Referees" of the system. They must be rigid.
- **Old Way:** Prompt engineering to beg the model for JSON.
- **BAML New Way:**
    ```rust
    class VerifierOutcome {
      status: "pass" | "fail" | "warn"
      reasoning: string
      breaking_changes: bool
    }

    function VerifyCode(diff: string) -> VerifierOutcome {
      client SkepticalClient
      prompt #" ... "#
    }
    ```
The Supervisor simply calls `b.VerifyCode(diff=...)` and gets a validated object or a raised exception if retries fail.

---

## 2. Integration Points

### 2.1 The Host (Supervisor)
The `RunOrchestrator` currently constructs prompts manually.
- **Change:** Migrate `supervisor/agent/prompts.py` to `baml_src/*.baml`.
- **Benefit:** `RunOrchestrator` becomes cleaner; logic focuses on *flow*, not *text*.

### 2.2 The E4 Register (Event Stream)
The `EventStore` needs to log "Thoughts" and "Status" in real-time.
- **Change:** Use `b.stream.FunctionName()`.
- **Benefit:** As tokens arrive, BAML constructs a `PartialVerifierOutcome`. We can emit `NOTE` events to the Event Bus with the partial reasoning *as it generates*, making the "Automatic Computer" feel alive and responsive.

### 2.3 Tools & Agents
Agents currently have tools defined in Python `pydantic` models.
- **Change:** Define tool schemas in BAML. BAML can inject these definitions into prompts natively.
- **Benefit:** We can generate the tool definition text for *any* model (OpenAI function calling format, Anthropic XML, etc.) automatically via BAML’s renderer, decoupling our tools from the model provider's specific API quirks.

---

## 3. Implementation Plan (The Application)

We don't do this "Big Bang" style. We use the **Spiral** approach.

### Phase 1: The Wedge (Verifiers)
*Target: Immediate (Spiral 3)*
- **Goal:** Ship the "Director Gate" using BAML.
- **Action:**
    1. `baml init` in `choirOS/`.
    2. Create `baml_src/clients.baml` defining `Calm` and `Skeptical`.
    3. Create `baml_src/verifier.baml` defining `VerifierOutcome`.
    4. Port `VerifierRunner.py` to use `baml_client`.

### Phase 2: The Abstraction (Orchestrator)
*Target: Next Sprint*
- **Goal:** Abstract model providers from the main run loop.
- **Action:**
    1. Define core agent loops (Plan, Execute) in BAML.
    2. Use BAML streaming to pipe "thought chains" directly to the UI via NATS.

### Phase 3: The Ecosystem (Tools & Agents)
*Target: Spiral 4*
- **Goal:** Enable user-defined tools via BAML.
- **Action:** Allow users to write `.baml` files in their workspace which the Supervisor hot-loads to create new Agent capabilities on the fly.

## Conclusion

Deep BAML integration is the specific unlock for **Spiral 3**. It converts "AI Vibe Checking" into "Systematic Verification" by enforcing schema strictness at the generation layer. We should proceed immediately with Phase 1.
