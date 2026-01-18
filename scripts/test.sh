#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export NATS_USER=${NATS_USER:-choiros_supervisor}
export NATS_PASSWORD=${NATS_PASSWORD:-local_supervisor}

SKIP_NATS=0
KEEP_NATS=${KEEP_NATS:-0}
DOCKER_COMPOSE=""
NATS_STARTED=0
STOPPED_CONTAINERS=()

print_usage() {
    echo "Usage: ./scripts/test.sh [--no-nats]"
    echo "  --no-nats   Skip starting NATS"
}

for arg in "$@"; do
    case "$arg" in
        --no-nats)
            SKIP_NATS=1
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg"
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

ensure_env_file() {
    if [ ! -f "$ROOT_DIR/api/.env" ]; then
        echo "api/.env missing; creating stub"
        cat > "$ROOT_DIR/api/.env" <<'EOF'
# Local overrides for ChoirOS
# Add AWS_BEARER_TOKEN_BEDROCK and AWS_REGION if needed.
EOF
    fi
}

start_nats() {
    if [ "$SKIP_NATS" -eq 1 ]; then
        return
    fi
    ensure_env_file
    detect_docker_compose
    if [ -z "$DOCKER_COMPOSE" ]; then
        echo "Docker Compose not available; skipping NATS start"
        return
    fi
    if $DOCKER_COMPOSE up -d nats; then
        NATS_STARTED=1
    else
        echo "Failed to start NATS via docker compose"
    fi
}

preflight_nats() {
    if [ "$SKIP_NATS" -eq 1 ]; then
        return
    fi
    detect_docker_compose
    if [ -n "$DOCKER_COMPOSE" ]; then
        local ids
        ids=$(docker ps --format '{{.ID}} {{.Ports}} {{.Names}}' | awk '/:4222->/ {print $1}')
        if [ -n "$ids" ]; then
            echo "Stopping containers using port 4222..."
            for id in $ids; do
                docker stop "$id" >/dev/null 2>&1 || true
                STOPPED_CONTAINERS+=("$id")
            done
        fi
    fi

    if command -v lsof >/dev/null 2>&1; then
        local holders
        holders=$(lsof -nP -iTCP:4222 -sTCP:LISTEN 2>/dev/null | tail -n +2 || true)
        if [ -n "$holders" ]; then
            local pids
            pids=$(echo "$holders" | awk '$1 ~ /nats/ {print $2}')
            if [ -n "$pids" ]; then
                echo "Killing leftover nats processes on port 4222..."
                kill $pids >/dev/null 2>&1 || true
            fi
        fi
    fi

    if command -v lsof >/dev/null 2>&1; then
        if lsof -nP -iTCP:4222 -sTCP:LISTEN >/dev/null 2>&1; then
            echo "Port 4222 still in use; cannot start NATS."
            exit 1
        fi
    fi
}

stop_nats() {
    if [ "$NATS_STARTED" -ne 1 ] || [ "$KEEP_NATS" -eq 1 ]; then
        return
    fi
    detect_docker_compose
    if [ -z "$DOCKER_COMPOSE" ]; then
        return
    fi
    $DOCKER_COMPOSE stop nats >/dev/null 2>&1 || true
}

trap stop_nats EXIT

preflight_nats
start_nats

if [ ! -d "$ROOT_DIR/choiros/node_modules" ]; then
    echo "Missing choiros/node_modules. Run ./scripts/setup.sh"
    exit 1
fi

cd "$ROOT_DIR/choiros"
npm run test:e2e
