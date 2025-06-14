# Multi-stage build for security and size optimization
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Security: Create non-root user
RUN useradd -m -u 1000 -s /bin/bash evaluator

# Copy Python packages from builder
COPY --from=builder /root/.local /home/evaluator/.local

# Create necessary directories with correct permissions
RUN mkdir -p /app /tmp/evaluation /var/log/crucible && \
    chown -R evaluator:evaluator /app /tmp/evaluation /var/log/crucible

# Copy application code
WORKDIR /app
COPY --chown=evaluator:evaluator . .

# Security: Switch to non-root user
USER evaluator

# Set Python path
ENV PATH=/home/evaluator/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "app.py", "--port", "8080"]