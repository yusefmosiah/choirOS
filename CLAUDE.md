# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ChoirOS is a web-based AI assistant with a desktop UI metaphor. It consists of:
- **Frontend**: React 19 + TypeScript + Vite (port 5173)
- **Backend**: FastAPI Python (port 8000) for parsing and artifacts
- **Supervisor**: FastAPI Python service (port 8001) for agent orchestration
- **NATS**: Message broker for real-time events (ws://localhost:8080)

## Development Commands

### Full Stack Development
```bash
./dev.sh              # Start frontend, backend, supervisor, NATS
./dev.sh stop         # Stop all dev processes
./dev.sh restart      # Stop all and restart
./dev.sh status       # Show status of all dev processes
./dev.sh nats-reset   # Stop NATS, remove JetStream data, restart
./dev.sh --no-nats    # Skip NATS container
```

### Test Harness
```bash
./scripts/test.sh --nats-integration   # Start NATS and run integration tests
./scripts/test.sh --skip-e2e           # Run non-E2E tests only
```

### Frontend (choiros/)
```bash
cd choiros
npm run dev          # Dev server (port 5173)
npm run build        # TypeScript check + Vite build
npm run lint         # ESLint checks
npm run test:e2e     # Playwright E2E tests
npm run test:e2e:ui  # Playwright with UI
```

### Backend (api/)
```bash
cd api
uvicorn api.main:app --reload --port 8000  # Dev server
pytest                                     # Run all tests
pytest -v                                  # Verbose output
pytest path/to/test_file.py                # Run specific file
pytest -k "test_name"                      # Run by pattern
```

### Supervisor (supervisor/)
```bash
cd supervisor
pytest                                     # All tests
pytest tests/test_event_contract.py        # Specific test file
SUPERVISOR_STANDALONE=1 python -m supervisor.main  # Standalone mode
```

## Environment Setup

### Python Virtual Environment
- Location: `api/venv` (created by `dev.sh`)
- Activate: `source api/venv/bin/activate`
- Set `PYTHONPATH` to repo root for absolute imports in supervisor modules

### Environment Variables
- Backend `.env` at `api/.env`
- NATS credentials configured via docker-compose
- `VITE_FRONTEND_SANDBOX=1` for sandboxed frontend execution

## High-Level Architecture

### The Machine (Control Plane)
The **Machine** (`supervisor/machine.py`) is the central orchestrator:
- Polls for work from the event store (SQLite or NATS)
- Selects modes based on AHDB (Agent Hypothesis Database) state
- Executes mode directives through a mode executor
- Manages mode transitions deterministically

### Mode Engine (Policy Layer)
The **Mode Engine** (`supervisor/mode_engine.py`) implements a state machine:
- **CALM**: Normal operation mode (default)
- **CURIOUS**: Read-only inquiry and research
- **SKEPTICAL**: Verification and adjudication
- **PARANOID**: High-risk operations with restrictions
- **BOLD**: Post-mitigation operations
- **CONTRITE**: Recovery mode after crashes

Each mode has specific tool allowlists, budgets, and behavioral constraints.

### Agent System
- **Agent Harness** (`supervisor/agent/harness.py`): Main execution engine
- **BAML Integration** (`supervisor/baml_client/`): Structured LLM interactions
- **Verifier Runner** (`supervisor/verifier_runner.py`): Validation and verification pipeline

### Event System
- **Event Contract** (`supervisor/event_contract.py`): Standardized event types
- **NATS JetStream**: Append-only event log for replication
- **SQLite**: Materialized projections for fast queries
- Subject format: `choiros.{user_id}.{source}.{event_type}`

### Storage Architecture
- **Event Sourcing**: All state changes are events
- **AHDB** (`supervisor/db.py`): Agent Hypothesis Database for system state
- **Artifacts**: File-based storage in `artifacts/` directory with SHA256 hashing
- **state.sqlite**: Events, files, conversations, tool calls

### Sandbox System
- **Sandbox Runner** (`supervisor/sandbox_runner.py`): Isolated execution environments
- **Sprites.dev Integration** (`supervisor/sprites_adapter.py`): Cloud-based sandboxing
- Features: checkpoint/restore, resource isolation, network policy

### Frontend Architecture
- **App Registry** (`choiros/src/lib/apps.ts`): Centralized app definitions
- **Window Manager** (`choiros/src/components/window/`): Desktop metaphor UI
- **Zustand Stores** (`choiros/src/stores/`): State management (events, windows, sources)
- **NATS Integration** (`choiros/src/lib/nats.ts`): Real-time event streaming

## Key Design Principles

1. **Event Sourcing**: All state changes are events; SQLite provides materialized views
2. **Capability Gating**: Tools are restricted per mode at the tool boundary
3. **Verification Pipeline**: All executions go through verification with attestations
4. **Single-Writer**: Only one write-capable Mode runs at a time
5. **Artifact Sharing**: Cross-mode sharing via artifact pointers, not raw file paths
6. **AHDB Authority**: AHDB updates require receipts/attestations, not LLM output alone
7. **Testing Discipline**: Every feature or fix must include automated tests and explicit PREDICTION → EXPERIMENT → OBSERVE criteria.

## Code Style Guidelines

### Python (FastAPI)
- **Imports**: Absolute imports from repo root (e.g., `from api.routers import parse`)
- **Formatting**: Black-formatted, 100-char line length
- **Types**: Type hints for all function signatures; Pydantic models for API schemas
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes
- **Error Handling**: `HTTPException` with proper status codes
- **Models**: Pydantic `BaseModel` for all request/response schemas

### TypeScript/React
- **Imports**: Absolute imports with `@/` prefix (configured in tsconfig)
- **Formatting**: ESLint + Prettier (handled by `npm run lint`)
- **Types**: TypeScript strict mode; explicit interfaces for props
- **Naming**: `camelCase` for variables/hooks, `PascalCase` for components
- **Hooks**: Custom hooks in `src/hooks/` with `use` prefix; use Zustand for state
- **Components**: Functional components; props interfaces named `ComponentNameProps`

### General Conventions
- **No comments**: Avoid adding comments unless explaining complex logic
- **No TODOs**: Address issues directly or create follow-up tasks
- **Tests**: Python uses `unittest`; E2E uses Playwright
- **Secrets**: Never commit .env files or credentials

## Services and Ports
- Frontend: http://localhost:5173
- Backend: http://localhost:8000 (API docs at /docs)
- Supervisor: http://localhost:8001
- NATS: ws://localhost:8080

## Important Specifications
See `docs/specs/` for detailed specifications:
- `CHOIR_EVENT_CONTRACT_SPEC.md`: Canonical event types and subjects
- `CHOIR_MACHINE_V0_SPEC.md`: Machine architecture and mode model
- `CHOIR_MOODS_SPEC.md`: Mode policies and guards
- `VERIFICATION_GREEN_THREADS_SPEC.md`: Verifier pipeline
