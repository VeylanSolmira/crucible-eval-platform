# Flower Dockerfile - Celery monitoring dashboard
ARG BASE_IMAGE=crucible-base

FROM ${BASE_IMAGE}

USER root

# Install Flower
RUN pip install --no-cache-dir flower==2.0.1

# Copy the same application code as Celery worker
COPY --chown=appuser:appuser celery-worker/*.py /app/celery-worker/
COPY --chown=appuser:appuser shared/ /app/shared/

# Set working directory to celery-worker (where tasks.py is)
WORKDIR /app/celery-worker

# Set environment
ENV SERVICE_NAME="flower" \
    PYTHONPATH="/app:${PYTHONPATH}"

# Labels
LABEL service="flower" \
      description="Celery monitoring dashboard" \
      version="1.0.0"

# Use appuser from base image
USER appuser

# Flower runs on port 5555 by default
EXPOSE 5555

# Run Flower with the tasks module
CMD ["celery", "-A", "tasks", "flower"]