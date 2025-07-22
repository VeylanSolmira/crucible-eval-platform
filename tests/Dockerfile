# Test runner image for running tests inside Kubernetes
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl for coordinator to create jobs
RUN curl -LO "https://dl.k8s.io/release/v1.28.0/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/

# Create test user
RUN useradd -m -u 1000 testrunner

# Set working directory
WORKDIR /app

# Copy test requirements - maintain directory structure
COPY tests/requirements.txt ./tests/
COPY shared/requirements/ ./shared/requirements/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r tests/requirements.txt

# Copy application code
COPY . .

# No symlinks needed - directories already use Python-compatible names

# Fix permissions
RUN chown -R testrunner:testrunner /app

# Switch to non-root user
USER testrunner

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV IN_CLUSTER_TESTS=true
ENV PYTHONPATH=/app

# Default command
CMD ["python", "-m", "pytest", "tests/", "-v"]