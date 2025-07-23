# Multi-stage build for Celery Worker
ARG BASE_IMAGE=crucible-platform/base

# Build stage - compile dependencies that need gcc
FROM ${BASE_IMAGE} AS builder

USER root

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Celery-specific requirements  
# Maintain directory structure to preserve relative paths
WORKDIR /tmp
COPY celery_worker/requirements.txt ./celery_worker/
COPY shared/requirements-utils.txt ./shared/
COPY shared/requirements/ ./shared/requirements/
COPY constraints.txt ./
RUN pip install --no-cache-dir -r celery_worker/requirements.txt
WORKDIR /app

# Runtime stage - no build tools
FROM ${BASE_IMAGE} AS runtime

# Copy installed packages and executables from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/celery /usr/local/bin/celery

# Copy application code
COPY --chown=appuser:appuser celery_worker/*.py /app/celery_worker/
COPY --chown=appuser:appuser shared/ /app/shared/

# Set working directory to app root for proper package imports
WORKDIR /app

# Set specific environment and Python path
ENV SERVICE_NAME="celery_worker" \
    C_FORCE_ROOT="false" \
    PYTHONPATH="/app"

# Labels
LABEL service="celery-worker" \
      description="Celery distributed task worker" \
      version="1.0.0"

# Use appuser from base image
USER appuser

# Default to worker, but allow override for beat, flower, etc.
CMD ["celery", "-A", "celery_worker.celery_app", "worker", "--loglevel=info"]