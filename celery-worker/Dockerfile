# Celery Worker Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 celeryuser

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=celeryuser:celeryuser . .

# Switch to non-root user
USER celeryuser

# Command will be specified in docker-compose.yml for flexibility
# Default to worker, but allow override for beat, flower, etc.
CMD ["celery", "-A", "tasks", "worker", "--loglevel=info"]