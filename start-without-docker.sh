#!/bin/bash
# CollAgent - Start Web Interface (without Docker)
#
# Copyright (C) 2026 Tuomo Sainio
# Licensed under AGPL-3.0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT=${COLLAGENT_PORT:-5050}

# Load .env file if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

# Check if at least one API key is set
if [ -z "$GOOGLE_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: No API key set"
    echo "Either create a .env file with GOOGLE_API_KEY or OPENAI_API_KEY"
    echo "Or set it with: export GOOGLE_API_KEY=your_key"
    exit 1
fi

# Check for virtual environment
if [ -d "$SCRIPT_DIR/venv" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
elif [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: No virtual environment found. Consider creating one:"
    echo "  python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
fi

echo "Starting CollAgent web interface on port $PORT..."
echo "Press Ctrl+C to stop"
echo ""

python "$SCRIPT_DIR/collagent.py" --web --port "$PORT"
