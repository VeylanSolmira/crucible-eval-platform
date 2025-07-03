# This expects crucible-base to be built first
FROM crucible-base AS executor-service

WORKDIR /app

# Copy requirements and install dependencies
COPY executor-service/requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy shared modules
COPY shared/generated /app/shared/generated
COPY shared/constants /app/shared/constants

# Set PYTHONPATH to include the app directory
ENV PYTHONPATH=/app:$PYTHONPATH

# Copy only the executor app
COPY executor-service/app.py /app/

# Set health check URL for executor service port
ENV HEALTH_CHECK_URL=http://localhost:8083/health

# Switch to non-root user
USER appuser

# Run the service
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8083"]