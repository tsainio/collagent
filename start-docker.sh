#!/bin/bash
# CollAgent - Start Web Interface (Docker)
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

# Check if at least one API key is set
if [ -z "$GOOGLE_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: No API key set"
    echo "Either create a .env file with GOOGLE_API_KEY or OPENAI_API_KEY"
    echo "Or set it with: export GOOGLE_API_KEY=your_key"
    exit 1
fi

# Check if container is already running
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "CollAgent is already running on port $PORT"
    echo "Stop it with: ./stop-docker.sh"
    exit 1
fi

# Remove any stopped container with same name
docker rm "$CONTAINER_NAME" 2>/dev/null

# Build image if it doesn't exist
if ! docker image inspect collagent:latest >/dev/null 2>&1; then
    echo "Docker image not found. Building collagent:latest..."
    docker build -t collagent:latest "$SCRIPT_DIR"
    if [ $? -ne 0 ]; then
        echo "Failed to build Docker image"
        exit 1
    fi
    echo ""
fi

echo "Starting CollAgent web interface on port $PORT..."
docker run -d \
    --name "$CONTAINER_NAME" \
    -p "${PORT}:${PORT}" \
    ${GOOGLE_API_KEY:+-e GOOGLE_API_KEY="$GOOGLE_API_KEY"} \
    ${OPENAI_API_KEY:+-e OPENAI_API_KEY="$OPENAI_API_KEY"} \
    ${BRAVE_SEARCH_API_KEY:+-e BRAVE_SEARCH_API_KEY="$BRAVE_SEARCH_API_KEY"} \
    ${TAVILY_API_KEY:+-e TAVILY_API_KEY="$TAVILY_API_KEY"} \
    collagent --web --port "$PORT"

if [ $? -eq 0 ]; then
    echo ""
    echo "CollAgent is running!"
    echo "Open http://localhost:${PORT} in your browser"
    echo ""
    echo "Note: The server is bound to 0.0.0.0 and accessible from your local network."
    echo ""
    echo "View logs: docker logs -f $CONTAINER_NAME"
    echo "Stop:      ./stop-docker.sh"
else
    echo "Failed to start CollAgent"
    exit 1
fi
