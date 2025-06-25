# This expects crucible-base to be built first
FROM crucible-base AS queue-worker

WORKDIR /app

# Copy only the queue worker app
COPY queue-worker/app.py /app/

# Update health check for queue worker port
RUN sed -i 's/localhost:8080/localhost:8084/g' /healthcheck.py

# Switch to non-root user
USER appuser

# Run the service
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8084"]