# API Gateway Service
FROM crucible-base AS api-gateway

WORKDIR /app

# Copy only the API gateway app
COPY api-gateway/app.py /app/

# Update health check for API gateway port
RUN sed -i 's/localhost:8080/localhost:8080/g' /healthcheck.py

# Switch to non-root user
USER appuser

# Run the service
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]