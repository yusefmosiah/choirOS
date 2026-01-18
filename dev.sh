#!/bin/bash
# ChoirOS Development Startup Script
# Runs both frontend and backend in parallel

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

MODE="start"
SKIP_NATS=0
KEEP_NATS=${KEEP_NATS:-0}
DOCKER_COMPOSE=""
NATS_STARTED=0

print_usage() {
    echo "Usage: ./dev.sh [start|stop|status] [--no-nats]"
    echo "  start    Start frontend, backend, supervisor (default)"
    echo "  stop     Stop NATS container started by docker compose"
    echo "  status   Show NATS container status"
    echo "  --no-nats  Skip starting NATS"
}

for arg in "$@"; do
    case "$arg" in
        start|stop|status)
            MODE="$arg"
            ;;
        --no-nats)
            SKIP_NATS=1
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown argument: $arg${NC}"
            print_usage
            exit 1
            ;;
    esac
done

detect_docker_compose() {
    if command -v docker >/dev/null 2>&1; then
        if docker compose version >/dev/null 2>&1; then
            DOCKER_COMPOSE="docker compose"
        elif command -v docker-compose >/dev/null 2>&1; then
            DOCKER_COMPOSE="docker-compose"
        fi
    fi
}

start_nats() {
    ensure_env_file
    if [ "$SKIP_NATS" -eq 1 ]; then
        return
    fi
    detect_docker_compose
    if [ -z "$DOCKER_COMPOSE" ]; then
        echo -e "${YELLOW}⚠ Docker Compose not available; skipping NATS start${NC}"
        return
    fi
    if ! $DOCKER_COMPOSE up -d nats; then
        echo -e "${YELLOW}⚠ Failed to start NATS via docker compose${NC}"
        return
    fi
    NATS_STARTED=1
}

stop_nats() {
    detect_docker_compose
    if [ -z "$DOCKER_COMPOSE" ]; then
        echo -e "${YELLOW}⚠ Docker Compose not available; cannot stop NATS${NC}"
        return
    fi
    $DOCKER_COMPOSE stop nats >/dev/null 2>&1 || true
}

show_status() {
    detect_docker_compose
    if [ -z "$DOCKER_COMPOSE" ]; then
        echo -e "${YELLOW}⚠ Docker Compose not available${NC}"
        return
    fi
    $DOCKER_COMPOSE ps nats
}

ensure_env_file() {
    if [ ! -f "api/.env" ]; then
        echo -e "${YELLOW}⚠ api/.env missing; creating stub${NC}"
        cat > api/.env <<'EOF'
# Local overrides for ChoirOS
# Add AWS_BEARER_TOKEN_BEDROCK and AWS_REGION if needed.
EOF
    fi
}

if [ "$MODE" = "stop" ]; then
    stop_nats
    exit 0
fi

if [ "$MODE" = "status" ]; then
    show_status
    exit 0
fi

echo -e "${GREEN}🎹 Starting ChoirOS Development Environment${NC}"
echo ""

# Check if we're in the choirOS directory
if [ ! -d "choiros" ] || [ ! -d "api" ]; then
    echo -e "${RED}Error: Run this script from the choirOS root directory${NC}"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    kill $FRONTEND_PID $BACKEND_PID $SUPERVISOR_PID 2>/dev/null
    if [ "$NATS_STARTED" -eq 1 ] && [ "$KEEP_NATS" -ne 1 ]; then
        stop_nats
    fi
    exit 0
}

trap cleanup SIGINT SIGTERM

# Setup Python virtual environment if needed
if [ ! -d "api/venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    cd api
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    pip install -r ../supervisor/requirements.txt
    cd ..
else
    source api/venv/bin/activate
fi

# Set PYTHONPATH to project root for absolute imports
export PYTHONPATH="${PWD}"
export NATS_ENABLED=1
export NATS_USER=${NATS_USER:-choiros_supervisor}
export NATS_PASSWORD=${NATS_PASSWORD:-local_supervisor}

echo -e "${GREEN}Starting NATS (docker compose)...${NC}"
start_nats

echo -e "${GREEN}Starting Backend (FastAPI on port 8000)...${NC}"
uvicorn api.main:app --reload --port 8000 &
BACKEND_PID=$!

echo -e "${GREEN}Starting Supervisor (port 8001)...${NC}"
SUPERVISOR_STANDALONE=1 python -m supervisor.main &
SUPERVISOR_PID=$!

echo -e "${GREEN}Starting Frontend (Vite on port 5173)...${NC}"
cd choiros
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}✅ ChoirOS is running!${NC}"
echo -e "   Frontend:   ${YELLOW}http://localhost:5173${NC}"
echo -e "   Backend:    ${YELLOW}http://localhost:8000${NC}"
echo -e "   Supervisor: ${YELLOW}http://localhost:8001${NC}"
echo -e "   API Docs:   ${YELLOW}http://localhost:8000/docs${NC}"
echo ""
echo -e "Press ${RED}Ctrl+C${NC} to stop"
echo ""

# Wait for any process to exit
wait $FRONTEND_PID $BACKEND_PID $SUPERVISOR_PID
