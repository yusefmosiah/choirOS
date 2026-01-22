# Deployment Plan & Architecture Refinement

## 1. Architectural Refinement: Host vs. Sandbox

To address the confusion: **Yes, Git and Auth live "Outside" the Sandbox.**

### The "Supervisor" (Host / Control Plane)
Runs on the metal (EC2) or a privileged container.
*   **Responsibilities**:
    *   **Identity & Auth**: Validates sessions, manages passkeys (`shared/auth.py`).
    *   **Persistence**: Holds the canonical state (SQLite/NATS), including the Event Log (AHDB).
    *   **Version Control**: Executes `git` operations on the canonical repositories.
    *   **Orchestration**: Decides *when* and *where* to spin up a sandbox.
*   **State**: Persistent (EBS volume / S3 / RDS).

### The "Sprite" (Sandbox / Userland)
Ephemeral execution environment (`sprites.dev` or isolated subprocess).
*   **Responsibilities**:
    *   **Execution**: Runs user code, tests, and the "ChoirOS Frontend" development server.
    *   **Materialization**: The Supervisor "hydrates" the sprite by checking out code into it.
*   **State**: Ephemeral. Discarded after use (though checkpoints can optimize startup).

## 2. Deployment Checklist & Strategy

### A. AHDB + Moods
*   **Status**: **Implemented** in `supervisor/db.py`.
*   **Action**: Ensure `mood` is populated during `Run` creation and used by the agent to influence behavior (e.g., `CALM` vs `URGENT`).
*   **Next Step**: Visualize AHDB state in the frontend (the "Animated Context Heatmap").

### B. AgentFS (SQLite as Filesystem)
*   **Concept**: Treat the entire user workspace as a SQLite database (like `fs-sqlite` or `turso`).
*   **Benefit**: Instant snapshots, time-travel, and ease of syncing to S3.
*   **Implementation**:
    *   Shift from direct filesystem writes in Supervisor to an abstraction layer.
    *   *Phase 1*: Keep using local FS but mirror writes to SQLite (already done via `file.write` events).
    *   *Phase 2*: Make SQLite the source of truth and FUSE-mount it or sync it to the Sandbox.

### C. Mind Map / animated context heatmap
*   **Concept**: Visual debugging tool for the "Stream of Consciousness".
*   **Implementation**: A React component subscribing to specific NATS subjects or querying `ahdb_state`.

### D. Unilateral Auditor
*   **Concept**: An independent agent giving "thumbs up/down" on changes.
*   **Placement**: Runs as a separate worker service, listening to `run.commit_request` events.

## 3. Deployment Steps (EC2 + Docker)

### Step 1: Production Dockerfile
Create a `Dockerfile.prod` for the Supervisor/API.
*   **Base**: `python:3.11-slim`.
*   **Content**: Copy code, install deps.
*   **Entry**: `supervisord` (not the python script, but a process manager) or just run the Supervisor which spawns API.

### Step 2: Infrastructure (EC2)
*   **Instance**: `t3.medium` or `large` (needs RAM for NATS + Python services).
*   **OS**: Ubuntu 22.04 / Amazon Linux 2023.
*   **Networking**: Open ports 80 (HTTP) -> 443 (HTTPS). Nginx as reverse proxy.
*   **Persistence**: Attach EBS volume for SQLite DBs and Checks.

### Step 3: CI/CD (GitHub Actions)
1.  **Build**: Docker build.
2.  **Test**: Run pytest.
3.  **Deploy**: SSH into EC2, `docker compose pull && docker compose up -d`.
4.  **Secrets**: stored in GitHub Secrets (`AWS_ACCESS_KEY`, `ANTHROPIC_KEY`, etc.).

### Step 4: Multi-tenancy
*   **Current State**: Single user (`DEFAULT_USER_ID`).
*   **Strategy**:
    *   Update `supervisor` to require Session Token for all operations.
    *   Use `user_id` from token to scope DB queries and NATS subjects (`user.{id}.*`).
    *   Spin up separate Sprites per user.

## 4. Immediate Next Actions
1.  **Refactor**: Ensure `supervisor` code explicitly separates "Host Code" from "Sandbox Code" paths.
2.  **AgentFS**: Prototype the "SQLite as FS" mirror.
3.  **Frontend**: Build the "Heatmap" visualization.
