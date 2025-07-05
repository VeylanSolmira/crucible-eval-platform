# This expects crucible-base to be built first
FROM crucible-base AS queue-service

WORKDIR /app

# Copy queue service code and shared contracts
COPY queue-service/app.py /app/
COPY shared/ /app/shared/

# Set Python path to include app directory
ENV PYTHONPATH=/app

# Update health check for queue service port
RUN sed -i 's/localhost:8080/localhost:8081/g' /healthcheck.py

# Switch to non-root user
USER appuser

# Run the service
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8081"]