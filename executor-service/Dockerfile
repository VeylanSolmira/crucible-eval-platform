# This expects crucible-base to be built first
FROM crucible-base AS executor-service

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy only the executor app
COPY app.py /app/

# Update health check for executor service port
RUN sed -i 's/localhost:8080/localhost:8083/g' /healthcheck.py

# Switch to non-root user
USER appuser

# Run the service
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8083"]