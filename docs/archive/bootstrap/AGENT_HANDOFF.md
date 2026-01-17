# Phase 3.1 Agent Platform - Handoff Document

**Date:** 2025-12-17
**Status:** ✅ Agent WebSocket bug fixed - connection and message sending working

> Legacy: predates the Director/Associate split. Use Ralph-in-Ralph docs for v0.

---

## What Was Built

### Infrastructure
| Component | Status | Location |
|-----------|--------|----------|
| Dockerfile | ✅ | `/Dockerfile` |
| docker-compose.yml | ✅ | `/docker-compose.yml` |
| dev.sh (local dev script) | ✅ | `/dev.sh` |

### Supervisor Package (`/supervisor/`)
| File | Purpose |
|------|---------|
| `main.py` | FastAPI server on port 8001, agent WebSocket endpoint |
| `file_history.py` | In-memory file change tracking for undo |
| `vite_manager.py` | Manages Vite subprocess (Docker only) |
| `agent/harness.py` | Claude via AWS Bedrock, processes prompts |
| `agent/tools.py` | 4 tools: read_file, write_file, edit_file, bash |

### Frontend Changes (`/choiros/src/`)
| File | Purpose |
|------|---------|
| `hooks/useAgent.ts` | WebSocket hook for agent communication |
| `components/desktop/Taskbar.tsx` | Integrated agent, shows connection status |
| `components/desktop/Taskbar.css` | Agent status indicator styles |

---

## Key Design Decisions

1. **PYTHONPATH-based imports** - All Python imports use absolute paths (`from api.routers import parse`) with PYTHONPATH set to project root for local/Docker compatibility

2. **SUPERVISOR_STANDALONE mode** - When `SUPERVISOR_STANDALONE=1`, supervisor skips spawning Vite/API subprocesses (for local dev where dev.sh runs them separately)

3. **Dynamic path detection** - Supervisor uses `PYTHONPATH` or file location to find project root, works both locally and in Docker

4. **AWS Bedrock** - Agent uses `anthropic.AnthropicBedrock` with model `anthropic.claude-opus-4-5-20251101-v1:0`, credentials from `api/.env`

---

## Current Bug

**Symptom:** Agent shows connected (green wifi icon), toast shows "Sending to agent...", but:
- No server log entry for agent prompt
- No response from agent
- No error messages

**Likely causes to investigate:**
1. WebSocket `sendPrompt` not actually sending (check wsRef.current state)
2. Server `/agent` endpoint not receiving data
3. Agent harness not yielding responses
4. JSON serialization issue between frontend and backend

**Key files to debug:**
- `/choiros/src/hooks/useAgent.ts` - lines 59-68 (sendPrompt function)
- `/supervisor/main.py` - lines 118-131 (agent_websocket endpoint)
- `/supervisor/agent/harness.py` - process() generator function

---

## How to Run

### Local Development
```bash
./dev.sh
# Opens: http://localhost:5174 (Vite), localhost:8000 (API), localhost:8001 (Supervisor)
```

### Docker
```bash
docker-compose up --build
# Opens: http://localhost:5173
```

---

## Environment Variables

Required in `/api/.env`:
```
AWS_BEARER_TOKEN_BEDROCK=your_token
AWS_REGION=us-east-1
```

---

## Test Commands

```bash
# Health checks
curl http://localhost:8001/health
curl http://localhost:8000/health

# Test WebSocket (wscat)
wscat -c ws://localhost:8001/agent
# Send: {"prompt": "hello"}
```

---

## Files Modified This Session

- `/Dockerfile` - Added PYTHONPATH
- `/docker-compose.yml` - Created
- `/dev.sh` - Created, runs all 3 services locally
- `/supervisor/*` - Created entire package
- `/choiros/src/hooks/useAgent.ts` - Created
- `/choiros/src/components/desktop/Taskbar.tsx` - Added agent integration
- `/api/main.py` - Changed to absolute imports
- `/api/routers/parse.py` - Changed to absolute imports
- `/api/routers/artifacts.py` - Changed to absolute imports
- `/api/services/artifact_store.py` - Changed to absolute imports
- `/api/requirements.txt` - Added lxml_html_clean
