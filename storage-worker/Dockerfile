# Storage Worker Service
FROM crucible-base AS storage-worker

WORKDIR /app

# Install storage dependencies
RUN pip install --no-cache-dir \
    redis[hiredis]==5.0.1 \
    aiohttp==3.9.1 \
    sqlalchemy==2.0.23 \
    psycopg2-binary==2.9.9 \
    alembic==1.12.1

# Copy storage worker and dependencies
COPY storage-worker/app.py /app/
COPY storage/ /app/storage/

# Update health check for storage worker port
RUN sed -i 's/localhost:8080/localhost:8085/g' /healthcheck.py

# Create data directory with proper ownership for file storage
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

# Switch to non-root user
USER appuser

# Run the service
CMD ["python", "app.py"]