# CollAgent - Docker Container
#
# Copyright (C) 2026 Tuomo Sainio
# Licensed under AGPL-3.0

FROM python:3.12-slim

# OCI Labels for Docker Hub
LABEL org.opencontainers.image.title="CollAgent"
LABEL org.opencontainers.image.description="AI-powered research collaborator discovery using Google Gemini"
LABEL org.opencontainers.image.authors="Tuomo Sainio"
LABEL org.opencontainers.image.source="https://github.com/tsainio/collagent"
LABEL org.opencontainers.image.licenses="AGPL-3.0"

WORKDIR /app

# Install system dependencies for WeasyPrint (PDF generation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY collagent.py LICENSE ./
COPY collagent/ ./collagent/

# Run as non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port for web mode
EXPOSE 5000

# Default entrypoint - pass --web to start web server
# CLI mode: docker run collagent -p "profile"
# Web mode: docker run -p 5000:5000 collagent --web
ENTRYPOINT ["python", "collagent.py"]
