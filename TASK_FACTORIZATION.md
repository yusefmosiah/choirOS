# Task Factorization: The Ralph Evolution

We are evolving the agent architecture in strictly defined stages to ensure stability, correctness, and composability.

## Stage 1: Simple Ralph Loop (Refactoring)
- **Goal**: Abstract the current agent logic into a reusable, generic loop.
- **Deliverable**: A `RalphLoop` class that handles:
  - Message history management
  - LLM API calls (Anthropic)
  - Tool execution dispatch (generic interface)
  - Output streaming
- **Input**: User prompt, System prompt, Tool definitions.
- **Output**: Stream of events (text, tool_use, tool_result).
- **Why**: This forms the fundamental "atomic unit" of agency that can be composed later.

## Stage 2: Agentic Ralph (Current State Preservation)
- **Goal**: Re-implement the current "ChoirOS Agent" using the `RalphLoop` abstraction.
- **Configuration**:
  - **Tools**: `read_file`, `write_file`, `edit_file`, `bash`, `git_*`.
  - **Prompt**: "You are the ChoirOS agent..."
- **Verification**: Ensure existing WebSocket functionality in `supervisor/main.py` remains unchanged.
- **Why**: Proves that the abstraction works for the existing use case.

## Stage 3: Ralph in Ralph (Director/Associate)
- **Goal**: Implement hierarchical agency using composed `RalphLoop` instances.
- **Director**:
  - Role: Planner & Verifier.
  - Tools: `delegate_task`, `review_evidence`.
  - Prompt: "You are the Director..."
- **Associate**:
  - Role: Executor.
  - Tools: Filesystem & Bash (same as Agentic Ralph).
  - Prompt: "You are the Associate..."
- **Structure**: Director receives user request -> Calls Associate (Task) -> Associate loops -> Returns Evidence -> Director verifies -> Returns to User.

## Stage 4: Sandbox
### 4a: Unified Sandbox
- **Goal**: Isolate the agent runtime.
- **Implementation**: Containerize the `supervisor` process or the agent runtime specifically. Docker/Podman integration.

### 4b: Per-Agent Sandbox
- **Goal**: Ephemeral isolation.
- **Implementation**: Spin up a new container for each Associate task.
- **Why**: Prevents side effects between tasks and allows for clean resets.

## Stage 5: Event Sourcing
- **Goal**: Robust, durable state and time-travel.
- **Implementation**:
  - Full NATS JetStream integration for all agent events (`agent.input`, `agent.think`, `tool.call`, `tool.result`).
  - Replay capabilities to restore state from zero.
  - **Note**: Currently partially implemented; needs standardization and hardening.
