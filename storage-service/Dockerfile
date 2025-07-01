# Storage Service Dockerfile
ARG BASE_IMAGE=crucible-base
FROM ${BASE_IMAGE}

WORKDIR /app

# Copy requirements and install dependencies
COPY storage-service/requirements.txt /app/storage-service/requirements.txt
RUN pip install --no-cache-dir -r /app/storage-service/requirements.txt

# Copy storage service code and shared contracts
COPY storage-service/ /app/storage-service/
COPY storage/ /app/storage/
COPY shared/ /app/shared/

# Set Python path to include app directory
ENV PYTHONPATH=/app

# Health check using Python (curl not available in base image)
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8082/health').read()" || exit 1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8082

# Run the storage service
CMD ["uvicorn", "storage-service.app:app", "--host", "0.0.0.0", "--port", "8082"]