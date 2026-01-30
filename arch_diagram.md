# ChoirOS Architecture Diagram

Generated: 2026-01-29

## System Overview

ChoirOS is a web-based AI assistant with a desktop UI metaphor, built on an event-sourced architecture with mode-based agent orchestration.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CHOIROS SYSTEM ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## High-Level Components

```
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│   Frontend       │      │    Backend       │      │   Supervisor     │
│   (choiros/)     │      │    (api/)        │      │ (supervisor/)    │
│                  │      │                  │      │                  │
│ React 19 + TS    │◄────►│ FastAPI Python   │◄────►│ FastAPI Python   │
│ Vite Dev Server  │      │ Port 8000        │      │ Port 8001        │
│ Port 5173        │      │                  │      │                  │
└────────┬─────────┘      └────────┬─────────┘      └────────┬─────────┘
         │                         │                         │
         │ WebSocket/NATS          │ HTTP/WebSocket          │ HTTP/WebSocket
         │                         │                         │
         └─────────────────────────┴─────────────────────────┘
                                        │
                                        ▼
                              ┌──────────────────┐
                              │   NATS JetStream │
                              │   Message Broker │
                              │   Port 8080      │
                              └──────────────────┘
```

---

## Layered Architecture

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                            PRESENTATION LAYER                                  │
├───────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                  │
│  │  Desktop UI    │  │  App Registry  │  │  Window Mgr    │                  │
│  │  (Desktop.tsx) │  │  (apps.ts)     │  │ (WindowManager)│                  │
│  └────────────────┘  └────────────────┘  └────────────────┘                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                  │
│  │  Zustand       │  │  NATS Client   │  │  HTTP Client   │                  │
│  │  Stores        │  │  (nats.ts)     │  │  (api.ts)      │                  │
│  └────────────────┘  └────────────────┘  └────────────────┘                  │
└───────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                            API LAYER                                           │
├───────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                  │
│  │  /parse        │  │  /artifacts    │  │  /auth         │                  │
│  │  Router        │  │  Router        │  │  Router        │                  │
│  └────────────────┘  └────────────────┘  └────────────────┘                  │
└───────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                            ORCHESTRATION LAYER                                 │
├───────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                  │
│  │  The Machine   │  │  Mode Engine   │  │  Run Orch.     │                  │
│  │ (machine.py)   │  │(mode_engine.py)│  │(run_orchestr.) │                  │
│  │                │  │                │  │                │                  │
│  │ - Polls events │  │ - Mode selects │  │ - CALM → VERIFY│                  │
│  │ - AHDB state   │  │ - Transitions  │  │ - SKEPTICAL    │                  │
│  │ - Emits dirs   │  │ - Guards       │  │ - Rollback     │                  │
│  └────────────────┘  └────────────────┘  └────────────────┘                  │
└───────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                            EXECUTION LAYER                                     │
├───────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                  │
│  │ Agent Harness  │  │   BAML Client  │  │  Tool Runner   │                  │
│  │ (harness.py)   │  │  (baml_client) │  │  (tools.py)    │                  │
│  │                │  │                │  │                │                  │
│  │ - Executes     │  │ - LLM calls    │  │ - File ops     │                  │
│  │ - Modes        │  │ - Streaming    │  │ - Network      │                  │
│  │ - Receipts     │  │ - Structured   │  │ - Git ops      │                  │
│  └────────────────┘  └────────────────┘  └────────────────┘                  │
│  ┌────────────────┐  ┌────────────────┐                                           │
│  │Verifier Runner │  │ Sandbox Runner │                                           │
│  │(verifier_run.) │  │(sandbox_runner)│                                           │
│  │                │  │                │                                           │
│  │ - Validates    │  │ - Sprites.dev  │                                           │
│  │ - Attests      │  │ - Checkpoints  │                                           │
│  │ - Green threads│  │ - Isolation    │                                           │
│  └────────────────┘  └────────────────┘                                           │
└───────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                            STORAGE LAYER                                       │
├───────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                  │
│  │ Event Store    │  │  AHDB (SQLite) │  │   Artifacts    │                  │
│  │  (db.py)       │  │                │  │   (/artifacts) │                  │
│  │                │  │                │  │                │                  │
│  │ - Event log    │  │ - Hypotheses   │  │ - SHA256 hash  │                  │
│  │ - NATS pub     │  │ - Assertions   │  │ - Content addr │                  │
│  │ - Materialized │  │ - State        │  │ - Immutable    │                  │
│  └────────────────┘  └────────────────┘  └────────────────┘                  │
│  ┌────────────────┐                                                           │
│  │NATS JetStream  │                                                           │
│  │                │                                                           │
│  │ - Append-only  │                                                           │
│  │ - Replication  │                                                           │
│  │ - Dedupe       │                                                           │
│  └────────────────┘                                                           │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Mode System (Policy Layer)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MODE ENGINE STATE MACHINE                           │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌─────────┐
    │  START  │
    └────┬────┘
         │
         ▼
    ┌───────────────────────────────────────────────────────┐
    │                                                       │
    │  crash_detected? ──────────────────►  CONTRITE        │
    │       │                                              │
    │       ▼                                              │
    │  no_demo? ─────────────────────────► CURIOUS          │
    │       │
    │       ▼
    │  verifier_failures? ────────────────► SKEPTICAL
    │       │
    │       ▼
    │  privilege_boundary? ─────────────────► PARANOID
    │       │
    │       ▼
    │  ┌─────────┐
    │  │  CALM   │ ◄────────────────────────────────────┐   │
    │  │ (default│  ◄────────────┐                      │   │
    │  │   mode) │               │                      │   │
    │  └─────────┘               │                      │   │
    │       │                    │                      │   │
    │       │ ambiguity/idk?     │ verified?           │   │
    │       ▼                    ▼                      │   │
    │   CURIOUS ◄────────── SKEPTICAL                  │   │
    │                              │                    │   │
    │                              │ hyperthesis?       │   │
    │                              ▼                    │   │
    │                          PARANOID ◄───────────────┘   │
    │                              │                        │
    │                              │ mitigations?           │
    │                              ▼                        │
    │                           BOLD ──────────────────────┘
    │
    └───────────────────────────────────────────────────────┘

MODE CONFIGURATIONS:
┌──────────┬──────────────────┬──────────────┬─────────────────┐
│   Mode   │    Capability    │   Write      │    Purpose      │
├──────────┼──────────────────┼──────────────┼─────────────────┤
│ CALM     │ Full tool access │ Yes          │ Normal ops      │
│ CURIOUS  │ Read-only        │ No           │ Inquiry/research│
│ SKEPTICAL│ Verification     │ Limited      │ Adjudication    │
│ PARANOID │ Restricted       │ Limited      │ High-risk ops   │
│ BOLD     │ Post-mitigation  │ Yes          │ After fixes     │
│ CONTRITE │ Recovery         │ No           │ After crash     │
└──────────┴──────────────────┴──────────────┴─────────────────┘
```

---

## Event Flow Architecture

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                         EVENT SOURCING & FLOW                                 │
└───────────────────────────────────────────────────────────────────────────────┘

USER ACTION
    │
    ▼
┌─────────────────┐     NATS SUBJECT FORMAT:
│ Frontend        │     "choiros.{user_id}.{source}.{event_type}"
│ (User clicks)   │
└────────┬────────┘
         │ WebSocket
         ▼
┌─────────────────┐
│ Backend API     │────► NATS JetStream (Append-only Log)
│ (api/routers)   │
└────────┬────────┘      │
         │               │
         │ HTTP          │ materialize
         ▼               ▼
┌─────────────────┐  ┌─────────────────┐
│ Supervisor      │  │   Event Store   │
│ Machine         │◄─│   (db.py)       │
│                 │  │                 │
│ Polls for work  │  │ - events table  │
│                 │  │ - conversations │
│                 │  │ - files         │
│                 │  │ - AHDB state    │
└────────┬────────┘  └─────────────────┘
         │
         │ ModeDirective
         ▼
┌─────────────────┐
│ Agent Harness   │
│ (harness.py)    │
│                 │
│ - BAML LLM call │
│ - Tool execution│
│ - Receipt emit  │
└────────┬────────┘
         │
         │ Receipt Events
         ▼
┌─────────────────┐
│ Verifier Runner │────► ATTESTATIONS
│                 │
│ - Validate      │
│ - Test          │
│ - Green threads │
└─────────────────┘
```

---

## Data Storage Architecture

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                         STORAGE ARCHITECTURE                                  │
└───────────────────────────────────────────────────────────────────────────────┘

NATS JetStream (Source of Truth for Events)
┌──────────────────────────────────────────────────────────────────────────────┐
│ Stream: CHOIR                                                                │
│ Subjects: choiros.{user_id}.{source}.{event_type}                            │
│                                                                              │
│ Event Types:                                                                 │
│  - Core: file.write, file.delete, message, tool.call, tool.result          │
│  - Mode: mode.start, mode.stop, mode.update, mode.heartbeat                 │
│  - Receipts: receipt.read, receipt.patch, receipt.verifier, receipt.ahdb... │
│  - Notes: note.observation, note.hypothesis, note.conjecture               │
│  - Artifacts: artifact.create, artifact.pointer                             │
└──────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 │ Subscribe & Materialize
                                 ▼
SQLite (Materialized Projections)
┌──────────────────────────────────────────────────────────────────────────────┐
│ Tables:                                                                      │
│                                                                              │
│ events (seq, nats_seq, event_id, timestamp, type, payload)                  │
│   ├── Source of truth projection from NATS                                  │
│   └── Append-only event log                                                 │
│                                                                              │
│ files (path, content_hash, blob_url, updated_at)                            │
│   ├── Materialized file state                                               │
│   └── Content-addressed via SHA256                                          │
│                                                                              │
│ conversations (id, started_at, title, last_seq)                             │
│   ├── Active chat sessions                                                   │
│   └── Links to event sequence                                               │
│                                                                              │
│ messages (id, conversation_id, event_seq, role, content, timestamp)        │
│   ├── Denormalized for query convenience                                    │
│   └── Links to events table                                                 │
│                                                                              │
│ work_items (id, status, created_at, updated_at, run_id, conversation_id)   │
│   ├── Queue for Machine processing                                          │
│   └── Status: pending/running/completed/failed                              │
│                                                                              │
│ ahdb (key, value, authority, evidence_seq, updated_at)                      │
│   ├── Agent Hypothesis Database                                             │
│   ├── authority: "proposed" | "asserted"                                    │
│   └── Evidence links to receipts                                            │
│                                                                              │
│ event_dedupe (nats_seq, delivery_count, first_seen, processed_at)          │
│   ├── Prevents duplicate event processing                                   │
│   └── Used by projector/auditor workers                                     │
│                                                                              │
│ sync_state (key, value, updated_at)                                         │
│   ├── Checkpoint/sync metadata                                              │
│   └── Sandbox checkpoint IDs                                                │
└──────────────────────────────────────────────────────────────────────────────┘

File System
┌──────────────────────────────────────────────────────────────────────────────┐
│ /artifacts/                                                                  │
│   ├── {sha256_hash}  (Content-addressed immutable storage)                  │
│   └── Used for cross-mode sharing via pointers                              │
│                                                                              │
│ state.sqlite                                                                 │
│   └── All materialized projections                                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Communication Details

### Frontend → Backend Communication
```
Frontend (choiros/)
    │
    ├── HTTP API (fetch)
    │   ├── POST /api/parse (execute agent)
    │   ├── GET /api/artifacts (list artifacts)
    │   ├── POST /api/artifacts (upload artifact)
    │   ├── POST /api/auth/login (authentication)
    │   └── GET /api/settings (provider config)
    │
    └── WebSocket (NATS)
        ├── Subscribe: choiros.{user_id}.>
        ├── Real-time events
        └── Auto-reconnect

State Management:
    ├── Zustand stores:
    │   ├── useEventsStore (event streaming)
    │   ├── useWindowsStore (window management)
    │   └── useSourcesStore (source tracking)
    │
    └── App Registry:
        └── Centralized app definitions (writer, files, terminal, mail, git, auth)
```

### Backend → Supervisor Communication
```
Backend API (api/)
    │
    ├── HTTP (internal)
    │   ├── POST /supervisor/run (execute mode)
    │   ├── GET /supervisor/status (machine status)
    │   └── POST /supervisor/stop (halt execution)
    │
    └── Shared SQLite (state.sqlite)
        ├── Append events
        ├── Query projections
        └── Access AHDB state

Key Routers:
    ├── parse.py - Agent execution endpoint
    ├── artifacts.py - Artifact storage/retrieval
    ├── auth.py - Authentication (shared tenancy)
    └── settings.py - Provider configuration
```

### Supervisor Internal Communication
```
Machine (machine.py)
    │
    ├── Polls EventStore
    │   └── SELECT * FROM work_items WHERE status='pending'
    │
    ├── Selects Mode (mode_engine.py)
    │   ├── Evaluates ModeInputs
    │   ├── Checks guards
    │   └── Returns mode_id
    │
    ├── Creates ModeDirective
    │   ├── mode_id
    │   ├── prompt
    │   ├── work_item_id
    │   ├── allow_write
    │   └── run_id
    │
    └── Executes via RunOrchestrator
        ├── CALM mode execution
        ├── Verification
        ├── SKEPTICAL adjudication
        └── Rollback on failure

Agent Harness (harness.py)
    │
    ├── Receives ModeDirective
    ├── Loads ModeConfig
    ├── Builds prompt (prompt_builder.py)
    ├── Calls BAML LLM
    ├── Executes tools (tools.py)
    ├── Emits receipts to EventStore
    └── Yields streaming results
```

---

## Agent Tools Architecture

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                            AGENT TOOLS (tools.py)                             │
└───────────────────────────────────────────────────────────────────────────────┘

Tool Categories:
┌────────────────────────┬─────────────────────────────────────────────────────┐
│ FILE OPERATIONS        │ - read_file(path, limit, offset)                    │
│                        │ - write_file(path, content)                         │
│                        │ - list_files(path, pattern)                         │
│                        │ - glob_files(pattern)                               │
│                        │ - search_files(path, pattern)                       │
│                        │ - create_directory(path)                            │
├────────────────────────┼─────────────────────────────────────────────────────┤
│ GIT OPERATIONS         │ - git_status()                                      │
│                        │ - git_diff(path)                                    │
│                        │ - git_log(limit)                                    │
│                        │ - git_commit(message, files)                        │
│                        │ - git_rollback()                                    │
├────────────────────────┼─────────────────────────────────────────────────────┤
│ EDITING                │ - edit_file(file_path, old_string, new_string)      │
│                        │ - replace_all(file_path, old_string, new_string)    │
├────────────────────────┼─────────────────────────────────────────────────────┤
│ EXECUTION              │ - run_bash(command, timeout, background)           │
│                        │ - spawn_agent(type, description, prompt)            │
│                        │ - get_task_output(task_id, block, timeout)          │
├────────────────────────┼─────────────────────────────────────────────────────┤
│ KNOWLEDGE BASE         │ - read_artifact(artifact_hash)                      │
│                        │ - create_artifact(content, mime_type)               │
│                        │ - list_artifacts(filters)                           │
├────────────────────────┼─────────────────────────────────────────────────────┤
│ AGENT STATE            │ - get_ahdb_state()                                  │
│                        │ - update_ahdb(delta, authority)                     │
│                        │ - get_conversation(id)                              │
├────────────────────────┼─────────────────────────────────────────────────────┤
│ VERIFICATION           │ - run_verifiers(plan_name, specs)                   │
│                        │ - list_verifier_plans()                             │
├────────────────────────┼─────────────────────────────────────────────────────┤
│ NETWORK                │ - web_search(query, domain_filter, recency)         │
│                        │ - fetch_url(url)                                    │
│                        │ - http_request(url, method, headers, body)          │
└────────────────────────┴─────────────────────────────────────────────────────┘

Capability Gating:
- Tools are filtered based on ModeConfig.tool_allowlist
- Each mode has explicit tool permissions
- Network access requires mode capability
- File writes require mode capability
```

---

## Verification Pipeline

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                     VERIFICATION GREEN THREADS                               │
└───────────────────────────────────────────────────────────────────────────────┘

CALM Mode Execution:
    │
    ├── Agent executes tools
    ├── Generates receipts
    │
    ▼
Verifier Runner (verifier_runner.py)
    │
    ├── Select verifier plan (verifier_plan.py)
    │   - test_basic (default)
    │   - test_e2e
    │   - test_security
    │   - test_performance
    │
    ├── Build verifier specs
    │   - Type checks
    │   - Linting
    │   - Unit tests
    │   - Integration tests
    │
    ├── Create sandbox (sandbox_runner.py)
    │   ├── Sprites.dev cloud sandbox
    │   ├── Restore last checkpoint
    │   └── Isolated environment
    │
    ├── Run verifiers in parallel (green threads)
    │   ├── pytest subprocess
    │   ├── Type checking
    │   ├── Linting
    │   └── Custom validators
    │
    └── Collect results
        ├── Pass → Continue
        ├── Fail → SKEPTICAL mode
        └── Crash → CONTRITE mode

SKEPTICAL Mode:
    │
    ├── Reviews verifier results
    ├── Analyzes failures
    ├── Proposes fixes
    │
    └── Returns to CALM or escalates to PARANOID

PARANOID Mode:
    │
    ├── High-risk operations
    ├── Strict verification
    ├── User approval required
    │
    └── If mitigations installed → BOLD mode

BOLD Mode:
    │
    ├── Post-mitigation operations
    ├── Validate fixes
    │
    └── Return to CALM if verified
```

---

## External Dependencies & Integrations

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL INTEGRATIONS                                  │
└───────────────────────────────────────────────────────────────────────────────┘

LLM Providers (provider_factory.py):
    ├── AWS Bedrock (Claude, etc.)
    ├── OpenAI (GPT models)
    └── Configurable via API settings

BAML (Boundary):
    ├── Type-safe LLM interactions
    ├── Streaming responses
    └── Structured output parsing

NATS JetStream:
    ├── Message broker
    ├── Event streaming
    ├── Deduplication
    └── Persistence

Sprites.dev (sandbox_adapter.py):
    ├── Cloud-based sandboxes
    ├── Checkpoint/restore
    ├── Resource isolation
    └── Network policy

Git:
    ├── Version control
    ├── Checkpoints
    ├── Rollback capability
    └── Diff generation
```

---

## Development Workflow

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                       DEVELOPMENT WORKFLOW                                    │
└───────────────────────────────────────────────────────────────────────────────┘

Startup (./dev.sh):
    │
    ├── Start NATS (docker-compose)
    ├── Start Backend (uvicorn api.main:app --port 8000)
    ├── Start Supervisor (uvicorn supervisor.main:app --port 8001)
    └── Start Frontend (cd choiros && npm run dev --port 5173)

User Flow:
    │
    ├── User opens → http://localhost:5173
    ├── Desktop UI renders
    ├── User types in command bar or opens app
    │
    ▼
Frontend → Backend API
    │
    ▼
Backend creates work_item in EventStore
    │
    ▼
Backend publishes event to NATS
    │
    ▼
Supervisor Machine polls EventStore
    │
    ▼
Machine selects mode → Creates directive
    │
    ▼
Agent Harness executes with BAML
    │
    ├── LLM planning
    ├── Tool execution
    ├── Receipt generation
    │
    ▼
Verifier Runner validates
    │
    ├── Pass → Complete
    ├── Fail → SKEPTICAL → Retry
    └── Crash → CONTRITE → Rollback
    │
    ▼
Results streamed to Frontend via NATS
```

---

## Testing Architecture

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                           TESTING STRATEGY                                    │
└───────────────────────────────────────────────────────────────────────────────┘

Test Layers:

1. Unit Tests (pytest)
   ├── supervisor/tests/
   │   ├── test_event_contract.py
   │   ├── test_db.py
   │   ├── test_mode_engine.py
   │   ├── test_nats_integration.py
   │   ├── test_event_dedupe.py
   │   └── test_research_*.py
   │
   └── api/tests/
       └── (API-specific tests)

2. Integration Tests
   ├── ./scripts/test.sh --nats-integration
   └── NATS-dependent tests

3. E2E Tests (Playwright)
   ├── choiros/tests/e2e/
   │   ├── eventstream.spec.ts
   │   └── (user workflow tests)
   │
   └── npm run test:e2e

PREDICTION / EXPERIMENT / OBSERVE Protocol:
    ├── PREDICTION: Hypothesis about behavior
    ├── EXPERIMENT: Test code + execution
    └── OBSERVE: Verification of prediction
```

---

## Key Design Patterns

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                         DESIGN PATTERNS                                       │
└───────────────────────────────────────────────────────────────────────────────┘

1. Event Sourcing
   ├── All state changes are events
   ├── Append-only log
   └── Materialized projections for queries

2. Mode Pattern
   ├── Capability-based access control
   ├── State machine transitions
   └── Single-writer enforcement

3. Receipt Pattern
   ├── Every operation emits a receipt
   ├── Receipts contain evidence/attestations
   └── AHDB updates require receipts

4. Artifact Pattern
   ├── Content-addressed storage (SHA256)
   ├── Immutable artifacts
   └── Cross-mode sharing via pointers

5. Verification Pattern
   ├── All executions go through verification
   ├── Green threads for parallel tests
   └── Attestations for security

6. Sandbox Pattern
   ├── Isolated execution environments
   ├── Checkpoint/restore capability
   └── Resource and network policy

7. PREDICTION/EXPERIMENT/OBSERVE
   ├── Hypothesis-driven development
   ├── Self-documenting tests
   └── Independently verifiable features
```

---

## Security Model

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                         SECURITY MODEL                                        │
└───────────────────────────────────────────────────────────────────────────────┘

Capability Gates:
    ├── Tool-level permissions (mode_config.tool_allowlist)
    ├── File write permissions (mode_config.data_scope.repo_write)
    ├── Network access (mode_config.data_scope.network)
    └── Model tier limits (mode_config.model_policy)

AHDB Authority:
    ├── LLM output alone cannot update AHDB
    ├── Requires receipts/attestations
    ├── Proposed vs Asserted state
    └── Evidence links to verify claims

Verification:
    ├── All code runs through verifiers
    ├── Attestations for security-sensitive ops
    ├── Sandbox isolation
    └── Rollback on crash/failure

Single-Writer:
    ├── Only one write-capable mode at a time
    ├── Prevents concurrent conflicts
    └── Deterministic state transitions
```

---

## File Structure Reference

```
choirOS/
├── api/                          # Backend API service
│   ├── routers/                  # FastAPI route handlers
│   │   ├── parse.py             # Agent execution endpoint
│   │   ├── artifacts.py         # Artifact storage
│   │   ├── auth.py              # Authentication
│   │   └── settings.py          # Provider config
│   └── main.py                   # FastAPI app entry
│
├── supervisor/                   # Agent orchestration service
│   ├── machine.py               # Control plane orchestrator
│   ├── mode_engine.py           # Mode state machine
│   ├── mode_config.py           # Mode configurations
│   ├── run_orchestrator.py      # CALM→VERIFY→SKEPTICAL flow
│   ├── db.py                    # Event store & AHDB
│   ├── event_contract.py        # Canonical event types
│   ├── nats_client.py           # NATS wrapper
│   ├── prompt_builder.py        # System prompt construction
│   ├── verifier_runner.py       # Verification pipeline
│   ├── verifier_plan.py         # Verifier plans
│   ├── sandbox_runner.py        # Sandbox execution
│   ├── sprites_adapter.py       # Sprites.dev integration
│   ├── agent/                   # Agent execution
│   │   ├── harness.py           # Main agent loop
│   │   ├── tools.py             # Tool implementations
│   │   └── auditor.py           # Receipt auditor
│   ├── baml_client/             # BAML integration
│   └── tests/                   # Supervisor tests
│
├── choiros/                      # Frontend React app
│   ├── src/
│   │   ├── components/
│   │   │   ├── desktop/         # Desktop UI
│   │   │   │   ├── Desktop.tsx  # Main desktop
│   │   │   │   ├── Icon.tsx     # App icons
│   │   │   │   ├── Taskbar.tsx  # Taskbar
│   │   │   │   └── EventStream.tsx
│   │   │   ├── window/          # Window manager
│   │   │   │   ├── WindowManager.tsx
│   │   │   │   └── Window.tsx
│   │   │   └── apps/            # App components
│   │   │       ├── Writer.tsx
│   │   │       ├── Files.tsx
│   │   │       ├── Terminal.tsx
│   │   │       ├── Mail.tsx
│   │   │       ├── GitPanel.tsx
│   │   │       └── Auth.tsx
│   │   ├── stores/              # Zustand state
│   │   │   ├── events.ts
│   │   │   ├── windows.ts
│   │   │   └── sources.ts
│   │   ├── lib/                 # Utilities
│   │   │   ├── apps.ts          # App registry
│   │   │   ├── nats.ts          # NATS client
│   │   │   ├── api.ts           # HTTP client
│   │   │   ├── auth.ts          # Auth utilities
│   │   │   └── event_contract.ts
│   │   ├── hooks/               # React hooks
│   │   │   └── useAgent.ts
│   │   ├── App.tsx              # Root component
│   │   └── main.tsx             # Entry point
│   └── tests/e2e/               # Playwright E2E tests
│
├── shared/                       # Shared Python modules
│   ├── auth.py                  # Authentication utilities
│   ├── tenancy.py               # Multi-user tenancy
│   └── auth_middleware.py       # Auth middleware
│
├── artifacts/                    # Content-addressed storage
│   └── {sha256_hash}            # Immutable artifacts
│
├── docs/specs/                   # Architecture specs
│   ├── CHOIR_EVENT_CONTRACT_SPEC.md
│   ├── CHOIR_MACHINE_V0_SPEC.md
│   ├── CHOIR_MOODS_SPEC.md
│   └── VERIFICATION_GREEN_THREADS_SPEC.md
│
├── config/                       # Configuration files
├── scripts/                      # Development scripts
│   └── test.sh                  # Test runner
├── dev.sh                        # Main dev launcher
├── docker-compose.yml            # Docker services (NATS)
├── state.sqlite                  # Materialized event store
└── CLAUDE.md                     # Project guide
```

---

## Port Reference

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                           PORT REFERENCE                                       │
└───────────────────────────────────────────────────────────────────────────────┘

Frontend (choiros/):      5173  (Vite dev server)
Backend API (api/):       8000  (FastAPI with /docs)
Supervisor:              8001  (FastAPI service)
NATS WebSocket:          8080  (ws://localhost:8080)
NATS Monitoring:         8222  (http://localhost:8222)
```

---

## Environment Variables

```
# Frontend (choiros/)
VITE_FRONTEND_SANDBOX=1        # Enable sandboxed execution

# Backend (api/)
DATABASE_URL=sqlite:///./state.sqlite
SECRET_KEY=...
CHOIROS_USER_ID=...

# Supervisor (supervisor/)
NATS_ENABLED=1
NATS_URL=ws://localhost:8080
NATS_USER=choiros
NATS_PASS=choiros
SUPERVISOR_STANDALONE=1        # Run without backend
PYTHONPATH=/path/to/choirOS    # For absolute imports

# Sandbox
CHOIR_SANDBOX_KEEP=0           # Keep sandboxes after execution
SPRITES_API_KEY=...
```

---

End of Architecture Diagram
