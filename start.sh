#!/bin/bash
# CollAgent - Start Web Interface
#
# Copyright (C) 2026 Tuomo Sainio
# Licensed under AGPL-3.0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT=${COLLAGENT_PORT:-5050}
CONTAINER_NAME="collagent-web"

# Load .env file if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

# Check if GOOGLE_API_KEY is set
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "Error: GOOGLE_API_KEY not set"
    echo "Either create a .env file with GOOGLE_API_KEY=your_key"
    echo "Or set it with: export GOOGLE_API_KEY=your_key"
    exit 1
fi

# Check if container is already running
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "CollAgent is already running on port $PORT"
    echo "Stop it with: ./stop.sh"
    exit 1
fi

# Remove any stopped container with same name
docker rm "$CONTAINER_NAME" 2>/dev/null

echo "Starting CollAgent web interface on port $PORT..."
docker run -d \
    --name "$CONTAINER_NAME" \
    -p "${PORT}:${PORT}" \
    -e GOOGLE_API_KEY="$GOOGLE_API_KEY" \
    collagent --web --port "$PORT"

if [ $? -eq 0 ]; then
    echo ""
    echo "CollAgent is running!"
    echo "Open http://localhost:${PORT} in your browser"
    echo ""
    echo "View logs: docker logs -f $CONTAINER_NAME"
    echo "Stop:      ./stop.sh"
else
    echo "Failed to start CollAgent"
    exit 1
fi
