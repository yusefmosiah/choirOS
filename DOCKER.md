# ChoirOS Docker Setup

Single command to run ChoirOS locally or in production.

## Quick Start

```bash
./run.sh dev
```

This starts:
- **Frontend**: http://localhost:5173 (with hot reload)
- **Backend**: http://localhost:8000 (API docs at /docs)
- **Supervisor**: http://localhost:8001
- **NATS**: http://localhost:8222 (monitoring)

## Commands

| Command | Description |
|---------|-------------|
| `./run.sh dev` | Start development mode (hot reload) |
| `./run.sh prod` | Start production mode (optimized) |
| `./run.sh build` | Build containers |
| `./run.sh stop` | Stop all services |
| `./run.sh restart` | Restart all services |
| `./run.sh logs` | Follow logs from all services |
| `./run.sh clean` | Remove all containers and volumes |

## How It Works

### Development Mode
- Source code mounted as volumes for live reloading
- Frontend runs Vite dev server
- Backend runs with `--reload` flag
- Changes to code reflect immediately

### Production Mode
- No volume mounts (code baked into image)
- Frontend built and served via preview server
- Backend runs without reload overhead
- Optimized for deployment

## Environment

Required: `api/.env` file with AWS credentials:
```
AWS_BEARER_TOKEN_BEDROCK=your_token
AWS_REGION=us-east-1
```

## Deployment

For production deployment:
1. Build image: `docker-compose build`
2. Push to registry
3. Run: `./run.sh prod` on target server
4. Or use: `docker-compose -f docker-compose.prod.yml up -d`

## Architecture

```
┌─────────────────┐
│   choiros-app   │
│                 │
│  ┌───────────┐  │
│  │ Frontend  │  │  → :5173
│  │  (Vite)   │  │
│  └───────────┘  │
│                 │
│  ┌───────────┐  │
│  │ Backend   │  │  → :8000
│  │ (FastAPI) │  │
│  └───────────┘  │
│                 │
│  ┌───────────┐  │
│  │Supervisor │  │  → :8001
│  │ (FastAPI) │  │
│  └───────────┘  │
└─────────────────┘
         │
         └──────→ ┌──────────┐
                   │   NATS   │  → :4222, :8222, :8080
                   └──────────┘
```
