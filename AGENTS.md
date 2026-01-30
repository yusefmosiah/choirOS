# Agent Notes for ChoirOS

## Project Overview
ChoirOS is a web-based AI assistant with a desktop UI. It consists of:
- **Frontend**: React 19 + TypeScript + Vite (port 5173)
- **Backend**: FastAPI Python (port 8000)
- **Supervisor**: FastAPI Python service for agent orchestration (port 8001)
- **NATS**: Message broker for real-time events (ws://localhost:8080)

## Environment Setup

### Python Virtual Environment
- Location: `api/venv` (created by `dev.sh`)
- Activate: `source api/venv/bin/activate`
- Set `PYTHONPATH` to repo root for absolute imports in supervisor modules

### Environment Variables
- Backend `.env` at `api/.env`
- NATS credentials configured via docker-compose

## Build, Lint, and Test Commands

### Frontend (choiros/)
```bash
cd choiros
npm run dev          # Start dev server (port 5173)
npm run build        # TypeScript check + Vite build
npm run lint         # ESLint checks
npm run preview      # Preview production build
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
# Use venv for tests that rely on supervisor deps (e.g., nats-py):
/Users/wiz/choirOS/api/venv/bin/python -m pytest path/to/test_file.py
```

### Supervisor (supervisor/)
```bash
cd supervisor
pytest                                     # All tests
pytest tests/test_event_contract.py        # Specific test file
SUPERVISOR_STANDALONE=1 python -m supervisor.main  # Standalone mode
# Use api/venv python for tests that import NATS or supervisor deps:
/Users/wiz/choirOS/api/venv/bin/python -m pytest tests/test_file.py
```

### Full Stack
```bash
./dev.sh              # Start frontend, backend, supervisor, NATS
./dev.sh --no-nats    # Skip NATS container
./dev.sh stop         # Stop all dev processes (frontend, backend, supervisor, NATS)
./dev.sh restart      # Stop all and restart
./dev.sh status       # Show status of all dev processes and NATS
```

### Test Harness
```bash
./scripts/test.sh --nats-integration   # Start NATS and run integration tests
./scripts/test.sh --skip-e2e           # Run non-E2E tests only
```

### Sandbox Configuration
```bash
# Use sprites.dev for sandboxed execution
echo "CHOIR_SANDBOX_PROVIDER=sprites" >> api/.env
# Token already configured in api/.env as SPRITES_API_TOKEN
```

## Code Style Guidelines

### Python (FastAPI)
- **Imports**: Absolute imports from repo root (e.g., `from api.routers import parse`)
- **Formatting**: Black-formatted, 100-char line length
- **Types**: Use type hints for all function signatures; Pydantic models for API schemas
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes
- **Error Handling**: Use `HTTPException` with proper status codes; wrap in try/except with meaningful messages
- **Docstrings**: Module-level for files, concise summaries for functions
- **Models**: Pydantic `BaseModel` for all request/response schemas

### TypeScript/React
- **Imports**: Absolute imports with `@/` prefix (configured in tsconfig)
- **Formatting**: ESLint + Prettier (handled by `npm run lint`)
- **Types**: TypeScript strict mode; explicit interfaces for props and store types
- **Naming**: `camelCase` for variables/hooks, `PascalCase` for components
- **Hooks**: Custom hooks in `src/hooks/` with `use` prefix; use Zustand for state
- **Components**: Functional components; props interfaces named `ComponentNameProps`
- **Error Handling**: Try/catch with console.error; UI shows user-friendly messages

### General Conventions
- **No comments**: Avoid adding comments unless explaining complex logic
- **No TODOs**: Address issues directly or create follow-up tasks
- **Tests**: Automated tests are required for all new features and fixes. Prefer PREDICTION → EXPERIMENT → OBSERVE framing.
- **Secrets**: Never commit .env files or credentials; use placeholder values

## PREDICTION / EXPERIMENT / OBSERVE Development Protocol

All agent development work MUST follow the PREDICTION/EXPERIMENT/OBSERVE pattern. This isn't just documentation - it's AHDB.

### What This Means

**PREDICTION/EXPERIMENT/OBSERVE is how agents learn.** Without explicit prediction and observation, code is just movement, not learning.

When you implement features:

1. **PREDICTION**: State your hypothesis clearly at the top of the feature/test
   - What will change?
   - What behavior will emerge?
   - What's the expected outcome?

2. **EXPERIMENT**: Implement the concrete action
   - The function, test, or change being made
   - Include setup, execution, and cleanup
   - Make it reproducible

3. **OBSERVE**: Explicit verification method
   - How do we KNOW the prediction was correct?
   - Concrete assertions or metrics
   - Edge cases covered

### Why This Matters

- **Machine-Actionable**: Agents can parse PREDICTION/EXPERIMENT/OBSERVE blocks
- **Buildable**: Later work can reference earlier hypotheses
- **Verifiable**: Every feature includes its own proof
- **AHDB-Compatible**: Hypotheses are first-class objects in our system

### Example Pattern

```python
def test_nats_dedup_prevents_duplicate_processing():
    """
    PREDICTION: Events delivered multiple times by NATS will be processed exactly once
    due to event_dedupe table tracking by (consumer, event_id) primary key.

    EXPERIMENT:
    1. Create NATS consumer with explicit ACK and short AckWait
    2. Publish 100 events
    3. Process first delivery but do NOT ACK
    4. Wait for AckWait timeout (triggers redelivery)
    5. Process second delivery
    6. Mark event done and ACK

    OBSERVE:
    - event_dedupe table shows delivery_count >= 2 for all events
    - Each event appears exactly once in events table (seq unique)
    - No duplicate work items created
    """
```

### Required Elements

Every test file for new features MUST include:
- A module-level docstring explaining the hypothesis
- Each test method with PREDICTION/EXPERIMENT/OBSERVE sections
- Edge cases explicitly covered in OBSERVE section
- Metrics or concrete assertions (not "should work" but "count == 1")

This makes our codebase a knowledge graph, not just code.

## Key Files and Patterns

### Event Contract
- Canonical event types defined in `supervisor/event_contract.py`
- Must stay in sync with `docs/specs/CHOIR_EVENT_CONTRACT_SPEC.md`
- Event format: `choiros.{user_id}.{source}.{event_type}` (e.g., `choiros.local.agent.file.write`)

### Stores (Frontend)
- Zustand stores in `choiros/src/stores/`
- Event store: `useEventStore` for real-time notifications
- Window store: `useWindowStore` for desktop window management

### NATS Communication
- Browser connects via WebSocket using `nats.ws`
- Events published/subscribed on subjects matching event contract
- Auth credentials fetched from supervisor endpoint
- **Note**: Frontend shows "NATS offline" until authenticated via the Auth app (passkey login)

## Services
- Backend: http://localhost:8000 (API docs at /docs)
- Supervisor: http://localhost:8001
- Frontend: http://localhost:5173
- NATS: ws://localhost:8080
