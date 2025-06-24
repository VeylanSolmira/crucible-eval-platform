# This expects crucible-base to be built first
FROM crucible-base AS executor-service

WORKDIR /app

# Install Docker client library (only executor needs this)
RUN pip install --no-cache-dir docker==6.1.3

# Copy only the executor app
COPY executor-service/app.py /app/

# Update health check for executor service port
RUN sed -i 's/localhost:8080/localhost:8083/g' /healthcheck.py

# Switch to non-root user
USER appuser

# Run the service
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8083"]