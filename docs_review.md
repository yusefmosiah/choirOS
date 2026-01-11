# ChoirOS Critical Review
**Date:** January 2026
**Reviewer:** Jules

## Executive Summary
ChoirOS has a strong conceptual foundation ("The Model is the Kernel") and a functional localized desktop environment. However, the implementation currently diverges significantly from the architectural vision, particularly regarding the "NATS as Source of Truth" thesis. The system is currently a "split-brain" architecture where the frontend (React) and backend (Supervisor/Python) operate with separate state models, bridged only by HTTP requests, rather than a shared event stream.

## 1. Architectural Integrity

### The "Split-Brain" Reality
*   **Vision:** NATS is the "kernel bus" and source of truth. All components (UI, Agent, Filesystem) react to events.
*   **Reality:**
    *   **Frontend:** `choiros/src/stores/events.ts` is a local, in-memory Zustand store. It is ephemeral and disconnected from the backend.
    *   **Backend:** `supervisor/db.py` implements a persistent SQLite event store and attempts to publish to NATS (if enabled).
    *   **The Gap:** There is no wiring between the backend NATS stream and the frontend. `choiros/src/lib/nats.ts` exists but is unused. The `EventStream` UI component visualizes local, temporary alerts, not the system's actual event log.

### Persistence & State
*   **Artifacts:** The `api` service (FastAPI) stores artifacts in a Python dictionary (`api/services/artifact_store.py`). This means all parsed content and agent outputs are lost if the API process restarts.
*   **Agent State:** The `supervisor` persists conversation history and tool calls to `state.sqlite`, which is good. However, this state is not accessible to the `api` service, creating two separate "brains" for the application.

## 2. Codebase Status

### Frontend (`choiros/`)
*   **Stubs:**
    *   `Mail.tsx`: Fully mocked with `SAMPLE_EMAILS`. No backend integration.
    *   `Terminal`: Listed in `Desktop.tsx` icons but seemingly not implemented in `components/apps`.
*   **Event Handling:** `EventStream.tsx` uses a local store that auto-clears events after 12 seconds. It is a notification system, not an event log visualizer as described in `ARCHITECTURE.md`.
*   **NATS Client:** `src/lib/nats.ts` provides a solid foundation (`nats.ws`) but is currently dead code.

### Backend (`api/` & `supervisor/`)
*   **Supervisor:**
    *   The `agent_harness` correctly logs to SQLite (`db.py`).
    *   It has `NATS_ENABLED` flags, but without consumers, this is "write-only" architecture.
*   **API:**
    *   `api/main.py` has hardcoded CORS origins (`localhost:5173`).
    *   Completely separate from the Supervisor's state.

## 3. Discrepancies: Docs vs. Code
| Feature | Documentation (`ARCHITECTURE.md`) | Codebase Reality |
| :--- | :--- | :--- |
| **Source of Truth** | NATS JetStream | SQLite (Supervisor) / RAM (Frontend & API) |
| **Event Stream** | "NATS is the authoritative event log" | Frontend uses local Zustand; NATS client unused |
| **Artifacts** | "Parsed content... stored in S3/R2" | In-memory Python dictionary |
| **Deployment** | "In-app deploy pipeline" | `dev.sh` / `supervisor.sh` scripts only |
| **Terminal** | Implemented App | Missing / Stub |

## 4. Risks & Technical Debt
1.  **Data Loss:** API artifacts are volatile.
2.  **State Drift:** The frontend has no way to know if the backend state changes (e.g., if the agent writes a file) unless it explicitly polls or triggers the action itself.
3.  **Security:** CORS and User IDs are hardcoded (`local`, `localhost`).
4.  **Mock Dependency:** The `Mail` app and other UI elements rely heavily on mocks, giving a false sense of completeness.

## 5. Conclusion
To realize the "Automatic Computer" vision, the immediate priority must be **closing the loop**: wiring the frontend NATS client to the Supervisor's event stream. The "Model is the Kernel" cannot be true until the UI is a function of the event log.
