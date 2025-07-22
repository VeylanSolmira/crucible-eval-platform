FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY dispatcher_service/requirements.txt ./dispatcher_service/
COPY shared/requirements/ ./shared/requirements/
COPY shared/requirements-utils.txt ./shared/
RUN pip install --no-cache-dir -r dispatcher_service/requirements.txt

# Copy application and shared modules
COPY dispatcher_service/app.py .
COPY shared/ ./shared/

# Create non-root user
RUN useradd -m -u 1000 dispatcher && \
    chown -R dispatcher:dispatcher /app

USER dispatcher

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8090/health')"

EXPOSE 8090

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8090"]