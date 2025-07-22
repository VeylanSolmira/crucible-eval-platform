# Storage Worker Service
ARG BASE_IMAGE=crucible-base
FROM ${BASE_IMAGE} AS storage_worker

WORKDIR /app

# Copy requirements and install dependencies
COPY storage_worker/requirements.txt /app/storage_worker/
COPY shared/requirements-utils.txt /app/shared/
COPY shared/requirements/ /app/shared/requirements/
RUN pip install --no-cache-dir -r /app/storage_worker/requirements.txt

# Copy storage worker and dependencies
# Note: This Dockerfile should be built from the repository root:
# docker build -f storage_worker/Dockerfile .
COPY storage_worker/app.py /app/
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