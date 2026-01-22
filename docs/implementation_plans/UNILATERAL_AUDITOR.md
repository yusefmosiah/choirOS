# Implementation Plan: The Unilateral Auditor

This plan outlines the steps to build the "Killer App" defined in the [Automatic Computer Position Paper](../automatic_computer_position_paper.md).

## Goal
Build the **Unilateral Auditor**: a persistent, self-critical agent that observes the user's work and generates "dissenting" context—finding blind spots, contradictions, and uncited assumptions.

## Phase 1: The Core "Dissent" Capability (BAML + Search)
Creating the logic for the Auditor to critique a given context using BAML and Web Search.

- **[ ] Update `baml_src/tools.baml`**
    - Define `WebSearch` tool schema.
- **[ ] Create `baml_src/auditor.baml`**
    - Define `Auditor` class/function.
    - specialized prompt: " You are the Unilateral Auditor. You do not summarize. You dissent."
- **[ ] Implement Web Search Tool**
    - Create `supervisor/agent/tools/web_search.py`.
    - Use `TavniyClient` or `Brave` API.
- **[ ] Create `supervisor/agent/auditor.py`**
    - Python wrapper around BAML generated code.
    - Implements the loop: `Plan -> Search -> Critique`.

## Phase 2: Writer Integration (The "Check" Button)
Allowing the user to invoke the Auditor directly from the Writer app.

- **[ ] Update `Supervisor` API**
    - Add `POST /agent/audit` endpoint (or reuse `/agent` socket with specific type).
    - Support streaming response (SSE or separate events).
- **[ ] Update `choiros/src/components/apps/Writer.tsx`**
    - Add "Audit Link" item to the `?` command menu.
    - When selected, prompt for URL (via `window.prompt` for MVP).
    - Send URL to `/agent/audit` via `fetch` with stream handling.
    - Insert "Audit Report" block into editor.

## Phase 3: The Background Loop (Event Trigger)
Making it "Automatic" by hooking into the event stream.

- **[ ] Create `supervisor/auditor_worker.py`**
    - Standalone process (or async task in Supervisor).
    - Subscribes to NATS `choir.events.*`.
    - **Filter**: Listens for `file.write` or `run.completed`.
    - **Debounce**: Don't audit every keystroke; wait for "settling".
- **[ ] Implementation**
    - On trigger -> Gather Context -> BAML Audit -> Save Note.

## Phase 4: Visualization (The "Mind Map" / "Heatmap")
Showing the Auditor's work without interrupting the user.

- **[ ] Frontend Component: `ContextHeatmap`**
    - Visualizes recent events and Auditor notes.
    - "Red" glow for critical audits/dissent.
    - Click to expand the critique.

## Verification Plan

### Automated Tests
- **Unit Test**: `test_auditor_prompt.py` to verify the prompt generates critiques on sample bad text.
- **Integration Test**: `test_auditor_loop.py` to ensure `file.write` event triggers an audit entry in DB.

### Manual Verification
1.  **Run `scripts/audit.py docs/DEPLOYMENT_PLAN.md`**.
2.  **Expectation**: The Auditor should critique the lack of "Rollback" details or "Security constraints" in the deployment plan.
3.  **Refinement**: Tweak prompt until it finds *useful* blind spots.
