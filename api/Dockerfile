# API Service - Microservices mode
FROM crucible-base AS api-service

WORKDIR /app

# Copy API requirements first for better layer caching
COPY api/requirements.txt /app/api/requirements.txt

# Install API dependencies
RUN pip install --no-cache-dir -r /app/api/requirements.txt

# Copy API service code and dependencies
# Note: This Dockerfile should be built from the repository root:
# docker build -f api/Dockerfile .
COPY api/ /app/api/
COPY storage/ /app/storage/

# Create data directory with proper ownership for file storage
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

# Health check already configured in base image

# Switch to non-root user
USER appuser

# Run the microservices gateway
CMD ["uvicorn", "api.microservices_gateway:app", "--host", "0.0.0.0", "--port", "8080"]
