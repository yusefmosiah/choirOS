#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SKIP_PYTHON=0
SKIP_NODE=0

print_usage() {
    echo "Usage: ./scripts/setup_worktree.sh [--skip-python] [--skip-node]"
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

main_worktree=""
current=""
while IFS= read -r line; do
    if [[ $line == worktree* ]]; then
        current=${line#worktree }
    elif [[ $line == branch* ]]; then
        branch=${line#branch }
        if [[ $branch == refs/heads/main ]]; then
            main_worktree=$current
            break
        fi
    fi
done < <(git worktree list --porcelain)

if [[ -n $main_worktree && -f "$main_worktree/api/.env" ]]; then
    if [[ -e "$ROOT_DIR/api/.env" ]]; then
        echo "api/.env already exists in this worktree."
    else
        ln -s "$main_worktree/api/.env" "$ROOT_DIR/api/.env"
        echo "Linked api/.env from main worktree."
    fi
else
    echo "Main worktree api/.env not found; creating stub in this worktree."
    mkdir -p "$ROOT_DIR/api"
    cat > "$ROOT_DIR/api/.env" <<'EOF_ENV'
# Local overrides for ChoirOS
# Add AWS_BEARER_TOKEN_BEDROCK and AWS_REGION if needed.
EOF_ENV
fi

mkdir -p "$ROOT_DIR/.context"

setup_args=()
if [[ $SKIP_PYTHON -eq 1 ]]; then
    setup_args+=("--skip-python")
fi
if [[ $SKIP_NODE -eq 1 ]]; then
    setup_args+=("--skip-node")
fi

"$ROOT_DIR/scripts/setup.sh" "${setup_args[@]}"

echo "Worktree setup complete."
