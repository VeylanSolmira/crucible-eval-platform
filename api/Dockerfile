# API Service - Microservices mode
FROM crucible-base AS api-service

WORKDIR /app

# Install storage dependencies for database access
RUN pip install --no-cache-dir \
    sqlalchemy==2.0.23 \
    psycopg2-binary==2.9.9

# Copy API service code and dependencies
COPY api/ /app/api/
COPY storage/ /app/storage/

# Create data directory with proper ownership for file storage
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

# Health check already configured in base image

# Switch to non-root user
USER appuser

# Run the microservices gateway
CMD ["uvicorn", "api.microservices_gateway:app", "--host", "0.0.0.0", "--port", "8080"]
