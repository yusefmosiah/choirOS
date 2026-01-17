#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SKIP_PYTHON=0
SKIP_NODE=0

print_usage() {
    echo "Usage: ./scripts/setup.sh [--skip-python] [--skip-node]"
}

for arg in "$@"; do
    case "$arg" in
        --skip-python)
            SKIP_PYTHON=1
            ;;
        --skip-node)
            SKIP_NODE=1
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

ensure_env_file() {
    if [ ! -f "$ROOT_DIR/api/.env" ]; then
        echo "api/.env missing; creating stub"
        cat > "$ROOT_DIR/api/.env" <<'EOF_ENV'
# Local overrides for ChoirOS
# Add AWS_BEARER_TOKEN_BEDROCK and AWS_REGION if needed.
EOF_ENV
    fi
}

setup_python() {
    if [ "$SKIP_PYTHON" -eq 1 ]; then
        return
    fi
    if [ ! -d "$ROOT_DIR/api/venv" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv "$ROOT_DIR/api/venv"
    fi
    # shellcheck disable=SC1091
    source "$ROOT_DIR/api/venv/bin/activate"
    pip install -r "$ROOT_DIR/api/requirements.txt"
    pip install -r "$ROOT_DIR/supervisor/requirements.txt"
}

setup_node() {
    if [ "$SKIP_NODE" -eq 1 ]; then
        return
    fi
    if [ ! -d "$ROOT_DIR/choiros/node_modules" ]; then
        echo "Installing frontend dependencies..."
        cd "$ROOT_DIR/choiros"
        npm install
        cd "$ROOT_DIR"
    fi
}

ensure_env_file
setup_python
setup_node

echo "Setup complete."
