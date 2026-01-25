#!/bin/bash
# ChoirOS Development Startup Script
# Runs frontend, backend, and supervisor in parallel

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# PID file for tracking running processes
PID_FILE=".dev.sh.pids"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MODE="start"
SKIP_NATS=0
KEEP_NATS=${KEEP_NATS:-0}
DOCKER_COMPOSE=""
NATS_STARTED=0

print_usage() {
    echo "Usage: ./dev.sh [start|stop|status|restart|nats-reset] [--no-nats]"
    echo "  start      Start frontend, backend, supervisor (default)"
    echo "  stop       Stop all dev processes and NATS container"
    echo "  restart    Stop all processes and restart"
    echo "  status     Show status of all dev processes"
    echo "  nats-reset Stop NATS, remove JetStream data, and restart"
    echo "  --no-nats  Skip starting NATS"
}

for arg in "$@"; do
    case "$arg" in
        start|stop|status|restart|nats-reset)
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

reset_nats() {
    detect_docker_compose
    if [ -z "$DOCKER_COMPOSE" ]; then
        echo -e "${RED}Docker Compose not available; cannot reset NATS${NC}"
        return 1
    fi
    echo -e "${YELLOW}Stopping NATS and removing JetStream data...${NC}"
    $DOCKER_COMPOSE down -v nats 2>/dev/null || true
    echo -e "${GREEN}NATS data cleared. Stale consumers removed.${NC}"
}

show_nats_status() {
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

load_pids() {
    if [ -f "$PID_FILE" ]; then
        source "$PID_FILE"
    else
        FRONTEND_PID=""
        BACKEND_PID=""
        SUPERVISOR_PID=""
        AUDITOR_PID=""
    fi
}

save_pids() {
    cat > "$PID_FILE" <<EOF
FRONTEND_PID="$FRONTEND_PID"
BACKEND_PID="$BACKEND_PID"
SUPERVISOR_PID="$SUPERVISOR_PID"
AUDITOR_PID="$AUDITOR_PID"
EOF
}

check_pid() {
    local pid=$1
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        return 0
    fi
    return 1
}

is_running() {
    load_pids
    check_pid "$FRONTEND_PID" || check_pid "$BACKEND_PID" || check_pid "$SUPERVISOR_PID" || check_pid "$AUDITOR_PID"
}

stop_all() {
    echo -e "${YELLOW}Stopping ChoirOS processes...${NC}"
    load_pids

    for pid in $FRONTEND_PID $BACKEND_PID $SUPERVISOR_PID $AUDITOR_PID; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            echo "  Stopped PID $pid"
        fi
    done

    rm -f "$PID_FILE"
    # Ensure reloader children are fully stopped
    if command -v lsof >/dev/null 2>&1; then
        lsof -ti tcp:8001 | xargs -r kill 2>/dev/null || true
    fi
    echo -e "${GREEN}All processes stopped${NC}"
}

show_status() {
    load_pids
    echo -e "${GREEN}ChoirOS Status${NC}"
    echo ""

    local running=0

    if check_pid "$FRONTEND_PID"; then
        echo -e "  Frontend:   ${GREEN}running${NC} (PID: $FRONTEND_PID, port 5173)"
        running=1
    else
        echo -e "  Frontend:   ${RED}stopped${NC}"
    fi

    if check_pid "$BACKEND_PID"; then
        echo -e "  Backend:    ${GREEN}running${NC} (PID: $BACKEND_PID, port 8000)"
        running=1
    else
        echo -e "  Backend:    ${RED}stopped${NC}"
    fi

    if check_pid "$SUPERVISOR_PID"; then
        echo -e "  Supervisor: ${GREEN}running${NC} (PID: $SUPERVISOR_PID, port 8001)"
        running=1
    else
        echo -e "  Supervisor: ${RED}stopped${NC}"
    fi

    if check_pid "$AUDITOR_PID"; then
        echo -e "  Auditor:    ${GREEN}running${NC} (PID: $AUDITOR_PID)"
        running=1
    else
        echo -e "  Auditor:    ${RED}stopped${NC}"
    fi

    echo ""
    show_nats_status

    if [ "$running" -eq 0 ]; then
        echo ""
        echo -e "Run ${YELLOW}./dev.sh start${NC} to start all services"
    fi
}

if [ "$MODE" = "stop" ]; then
    stop_all
    stop_nats
    exit 0
fi

if [ "$MODE" = "status" ]; then
    show_status
    exit 0
fi

if [ "$MODE" = "nats-reset" ]; then
    stop_all
    reset_nats
    echo -e "${GREEN}Run ./dev.sh start to restart services${NC}"
    exit 0
fi

if [ "$MODE" = "restart" ]; then
    stop_all
    reset_nats
    echo ""
fi

if is_running; then
    echo -e "${YELLOW}ChoirOS is already running${NC}"
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
    load_pids
    kill $FRONTEND_PID $BACKEND_PID $SUPERVISOR_PID $AUDITOR_PID 2>/dev/null
    rm -f "$PID_FILE"
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
export SUPERVISOR_RELOAD=${SUPERVISOR_RELOAD:-0}

echo -e "${GREEN}Starting NATS (docker compose)...${NC}"
start_nats

echo -e "${GREEN}Starting Backend (FastAPI on port 8000)...${NC}"
uvicorn api.main:app --reload --port 8000 &
BACKEND_PID=$!

echo -e "${GREEN}Starting Supervisor (port 8001)...${NC}"
SUPERVISOR_STANDALONE=1 python -m supervisor.main &
SUPERVISOR_PID=$!

echo -e "${GREEN}Starting Auditor Worker...${NC}"
python supervisor/auditor_worker.py &
AUDITOR_PID=$!

echo -e "${GREEN}Starting Frontend (Vite on port 5173)...${NC}"
cd choiros
npm run dev &
FRONTEND_PID=$!
cd ..

# Save PIDs
save_pids

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
wait $FRONTEND_PID $BACKEND_PID $SUPERVISOR_PID $AUDITOR_PID
