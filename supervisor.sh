#!/bin/bash
# Run supervisor locally for development
# Requires: pip install -r supervisor/requirements.txt

cd "$(dirname "$0")"

# Check if virtual environment exists in api/
if [ -d "api/venv" ]; then
    source api/venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv api/venv
    source api/venv/bin/activate
fi

# Install supervisor requirements
pip install -q -r supervisor/requirements.txt 2>/dev/null

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo "Starting supervisor on port 8001..."
python -c "from supervisor.main import main; main()"
