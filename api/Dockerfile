# Multi-stage build for API Service
ARG BASE_IMAGE=crucible-base

# Build stage - install API-specific dependencies
FROM ${BASE_IMAGE} AS builder

# Switch to root for dependency installation
USER root

# Copy and install API-specific requirements
# Maintain directory structure to preserve relative paths
WORKDIR /tmp
COPY api/requirements.txt ./api/
COPY shared/requirements-utils.txt ./shared/
COPY shared/requirements/ ./shared/requirements/
RUN pip install --no-cache-dir -r api/requirements.txt
WORKDIR /

# Runtime stage - minimal final image
FROM ${BASE_IMAGE} AS runtime

# Copy installed packages from builder
# Python packages are in /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy only necessary application code with proper ownership
COPY --chown=appuser:appuser api/microservices_gateway.py api/__init__.py /app/api/
COPY --chown=appuser:appuser api/celery_client.py api/celery_constants.py /app/api/
COPY --chown=appuser:appuser storage/ /app/storage/
COPY --chown=appuser:appuser shared/ /app/shared/

# Create data directory
RUN mkdir -p /app/data && chown appuser:appuser /app/data

# Set specific environment for API service
ENV SERVICE_NAME="api-gateway" \
    HEALTH_CHECK_URL="http://localhost:8080/health"

# Expose port
EXPOSE 8080

# Labels
LABEL service="api-gateway" \
      description="API Gateway for Crucible Platform" \
      version="1.0.0"

# Switch to non-root user
USER appuser

# Run the microservices gateway
CMD ["uvicorn", "api.microservices_gateway:app", "--host", "0.0.0.0", "--port", "8080"]
