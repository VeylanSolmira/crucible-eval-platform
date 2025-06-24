FROM crucible-base AS worker-service

# We need Docker CLI for execution
RUN apt-get update && apt-get install -y \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire source directory (for execution engines)
COPY src/ /app/src/
COPY worker-service/app.py /app/

# Update health check for worker service port
RUN sed -i 's/localhost:8080/localhost:8082/g' /healthcheck.py

# Worker needs to run as root for Docker access
# (In production, use rootless Docker or other solutions)
USER root

# Run the service
CMD ["python", "app.py"]