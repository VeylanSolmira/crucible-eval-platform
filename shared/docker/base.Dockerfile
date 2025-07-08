# Optimized base image without venv complexity
FROM python:3.11-slim AS python-base

# Set Python environment variables for optimization
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LOG_LEVEL=INFO

# Create non-root user with explicit UID 1000 for volume compatibility
RUN groupadd -g 1000 appuser && useradd -u 1000 -g 1000 appuser \
    && mkdir -p /app \
    && chown -R appuser:appuser /app

# Install common dependencies in one layer
COPY shared/docker/requirements-base.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements-base.txt \
    && rm -f /tmp/requirements-base.txt

# Add optimized health check script
COPY --chown=appuser:appuser shared/docker/healthcheck.py /healthcheck.py
RUN chmod +x /healthcheck.py

# Set working directory
WORKDIR /app

# Default health check (services can override)
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python /healthcheck.py || exit 1

# Labels for better container management
LABEL maintainer="Crucible Platform Team" \
      description="Base image for Crucible Python services" \
      version="1.1.0"