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
```

### Supervisor (supervisor/)
```bash
cd supervisor
pytest                                     # All tests
pytest tests/test_event_contract.py        # Specific test file
SUPERVISOR_STANDALONE=1 python -m supervisor.main  # Standalone mode
```

### Full Stack
```bash
./dev.sh           # Start frontend, backend, supervisor, NATS
./dev.sh --no-nats # Skip NATS container
./dev.sh stop      # Stop NATS only
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
- **Tests**: Python uses `unittest`; E2E uses Playwright; unit tests inline with code
- **Secrets**: Never commit .env files or credentials; use placeholder values

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

## Services
- Backend: http://localhost:8000 (API docs at /docs)
- Supervisor: http://localhost:8001
- Frontend: http://localhost:5173
- NATS: ws://localhost:8080
