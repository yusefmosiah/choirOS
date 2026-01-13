# Agent Notes for ChoirOS

## Environment
- Use the Python virtual environment at `api/venv` (created by `dev.sh`).
- Activate with `source api/venv/bin/activate` when running Python tools.
- Set `PYTHONPATH` to the repo root when running supervisor modules.

## Development Script
- `./dev.sh` starts the frontend, backend, and supervisor.
- Supervisor standalone mode uses `SUPERVISOR_STANDALONE=1` and `NATS_ENABLED=0`.

## Services
- Backend: `http://localhost:8000`
- Supervisor: `http://localhost:8001`
- Frontend: `http://localhost:5173`
