#!/bin/bash
# CollAgent - Stop Web Interface
#
# Copyright (C) 2026 Tuomo Sainio
# Licensed under AGPL-3.0

CONTAINER_NAME="collagent-web"

if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Stopping CollAgent..."
    docker stop "$CONTAINER_NAME" >/dev/null
    docker rm "$CONTAINER_NAME" >/dev/null
    echo "CollAgent stopped"
else
    echo "CollAgent is not running"
    # Clean up any stopped container
    docker rm "$CONTAINER_NAME" 2>/dev/null
fi
