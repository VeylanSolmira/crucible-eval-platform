# Multi-stage build for Celery Worker
ARG BASE_IMAGE=crucible-base

# Build stage - compile dependencies that need gcc
FROM ${BASE_IMAGE} AS builder

USER root

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Celery-specific requirements
COPY celery-worker/requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Runtime stage - no build tools
FROM ${BASE_IMAGE} AS runtime

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy application code
COPY --chown=appuser:appuser celery-worker/*.py /app/celery-worker/
COPY --chown=appuser:appuser shared/ /app/shared/

# Set working directory to celery-worker
WORKDIR /app/celery-worker

# Set specific environment
ENV SERVICE_NAME="celery-worker" \
    C_FORCE_ROOT="false"

# Labels
LABEL service="celery-worker" \
      description="Celery distributed task worker" \
      version="1.0.0"

# Use appuser from base image
USER appuser

# Default to worker, but allow override for beat, flower, etc.
CMD ["celery", "-A", "tasks", "worker", "--loglevel=info"]