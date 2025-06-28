# Storage Worker Service
FROM crucible-base AS storage-worker

WORKDIR /app

# Copy requirements and install dependencies
COPY storage-worker/requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy storage worker and dependencies
# Note: This Dockerfile should be built from the repository root:
# docker build -f storage-worker/Dockerfile .
COPY storage-worker/app.py /app/
COPY storage/ /app/storage/
COPY shared/ /app/shared/

# Set Python path to include app directory
ENV PYTHONPATH=/app

# Update health check for storage worker port
RUN sed -i 's/localhost:8080/localhost:8085/g' /healthcheck.py

# Create data directory with proper ownership for file storage
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

# Switch to non-root user
USER appuser

# Run the service
CMD ["python", "app.py"]