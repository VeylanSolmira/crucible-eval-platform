# Execution Engine Service - PLACEHOLDER
# This Dockerfile is a placeholder for future microservice deployment

FROM python:3.9-slim

WORKDIR /app

# Install Docker client for Docker-in-Docker capability
RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/*

# Future: Copy requirements and install
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Future: Run as standalone service
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]

# Current: This service is used as a library in the monolithic platform
CMD ["echo", "Execution Engine is currently used as a library, not a standalone service"]
