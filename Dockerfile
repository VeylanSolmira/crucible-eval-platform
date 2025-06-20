# Multi-stage Dockerfile for Crucible Platform

# Build stage - install dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Copy just requirements first for better caching
COPY requirements.txt .

# Install dependencies from requirements.txt
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage - minimal final image
FROM python:3.11-slim

WORKDIR /app

# Install Docker CLI for sibling container management
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg && \
    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    # Add Docker repository
    echo \
      "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
      "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    # Install Docker CLI only (not the daemon)
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli && \
    # Clean up
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user first
RUN useradd -m -u 1000 -s /bin/bash appuser

# Copy installed packages from builder to appuser's home
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Make sure scripts in .local are on PATH
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/home/appuser/.local/lib/python3.11/site-packages:$PYTHONPATH

# Copy application code
COPY app.py .
COPY src/ ./src/
COPY api/ ./api/
COPY storage/ ./storage/
COPY requirements.txt .

# Create data directory for runtime data and set ownership
RUN mkdir -p /app/data && \
    chmod 755 /app/data && \
    chown -R appuser:appuser /app

# PRAGMATIC DECISION: Running as root for Docker socket access
# In production, this would be handled differently:
# - Kubernetes Jobs for execution (no docker socket needed)
# - Separate execution service with limited permissions
# - Docker socket proxy for controlled access
#
# For this demo/prototype, we accept the security trade-off
# to keep the architecture simple and focus on core functionality.
#
# See docs/architecture/pragmatic-security-decisions.md for details

# Note: We keep appuser created above for file ownership
# but don't switch to it for runtime

# Previous approach using gosu (removed for simplicity):
# RUN apt-get update && apt-get install -y gosu && rm -rf /var/lib/apt/lists/*
# COPY entrypoint.sh /entrypoint.sh
# RUN chmod +x /entrypoint.sh
# ENTRYPOINT ["/entrypoint.sh"]

# USER appuser  # Commented out - need root for Docker socket

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    DOCKER_HOST=unix:///var/run/docker.sock \
    STORAGE_BASE=/app/storage

# Expose the application port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/status || exit 1

# Default command - no complex entrypoint needed when running as root
CMD ["python", "app.py", "--port", "8080"]