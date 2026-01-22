# Implementation Plan: The Unilateral Auditor

This plan outlines the steps to build the "Killer App" defined in the [Automatic Computer Position Paper](../automatic_computer_position_paper.md).

## Goal
Build the **Unilateral Auditor**: a persistent, self-critical agent that observes the user's work and generates "dissenting" context—finding blind spots, contradictions, and uncited assumptions.

## Phase 1: The Core "Dissent" Capability
Creating the logic for the Auditor to critique a given context.

- **[ ] Create `supervisor/agent/auditor_prompt.py`**
    - Define the system prompt for the Auditor.
    - Key trait: "You do not summarize. You dissent. You look for blind spots."
- **[ ] Create `supervisor/agent/auditor.py`**
    - Extend or adapt `AgentHarness` to run in "Auditor Mode".
    - Input: A "Snapshot" of context (recent events, file content, AHDB state).
    - Output: A generic "Audit Note" (JSON).

## Phase 2: Manual Trigger (The "Check" Button)
Allowing the user to explicitly invoke the Auditor on a specific file or topic.

- **[ ] Add API Endpoint `POST /run/audit`**
    - Accepts `target_uri` or `text`.
    - Spawns an Auditor agent run.
- **[ ] Update `supervisor/db.py`**
    - Ensure `EventStore` can store `note.audit` events.
    - (Already supports generic notes, but we might want structured schemas).
- **[ ] CLI Tool `scripts/audit.py`**
    - `python scripts/audit.py <filename>` -> prints critique to stdout.

## Phase 3: The Background Loop (Event Trigger)
Making it "Automatic" by hooking into the event stream.

- **[ ] Create `supervisor/auditor_worker.py`**
    - Standalone process (or async task in Supervisor).
    - Subscribes to NATS `choir.events.*` (or polls SQLite if NATS disabled).
    - **Filter**: Listens for `file.write` or `run.completed`.
    - **Debounce**: Don't audit every keystroke; wait for "settling".
- **[ ] Integration**
    - On trigger -> Gather Context -> Run Auditor Agent -> Save Note.

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
