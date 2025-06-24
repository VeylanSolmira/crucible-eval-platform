FROM python:3.11-slim AS python-base

# Common dependencies for all services
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    pydantic==2.5.0 \
    httpx==0.25.0 \
    python-dotenv==1.0.0 \
    structlog==23.2.0 \
    requests==2.31.0 \
    redis[hiredis]==5.0.1

# Common setup
WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Health check script (common for all services)
RUN echo '#!/usr/bin/env python3\n\
import sys\n\
import httpx\n\
try:\n\
    response = httpx.get("http://localhost:8080/health", timeout=3)\n\
    sys.exit(0 if response.status_code == 200 else 1)\n\
except:\n\
    sys.exit(1)' > /healthcheck.py && chmod +x /healthcheck.py

# Default health check (services can override)
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python /healthcheck.py || exit 1