# Dockerization Strategy

## Overview

This document outlines our approach to containerizing the Crucible platform, including the decision to use sibling containers and our evolution path from monolith to microservices.

## Container Registry: Amazon ECR

We're using Amazon ECR (Elastic Container Registry) for the following reasons:
- **Native AWS Integration**: IAM roles work seamlessly, no separate credentials
- **Private by Default**: Better security for our platform
- **Already on AWS**: No additional infrastructure needed
- **Cost Effective**: ~$0.10/GB/month is reasonable for our needs

## Deployment Trigger Strategy

### Current Approach: Manual Restart
The EC2 instance pulls new images when systemd restarts the service:

```ini
# /etc/systemd/system/crucible-platform.service
[Service]
ExecStartPre=/usr/bin/docker pull $ECR_URL/crucible:latest
ExecStart=/usr/bin/docker run ...
```

### What Triggers Restart?

1. **Manual Deployment** (Current):
   ```bash
   # In GitHub Actions deployment
   aws ssm send-command \
     --instance-ids $INSTANCE_ID \
     --document-name "AWS-RunShellScript" \
     --parameters "commands=['sudo systemctl restart crucible-platform']"
   ```

2. **Automated Triggers** (Future Options):
   - **Webhook from ECR**: ECR → EventBridge → Lambda → SSM Command
   - **Polling Script**: Cron job checking for new images
   - **GitHub Actions**: Direct restart after successful push
   - **Watchtower**: Container that auto-updates other containers

For now, we'll stick with manual restart via GitHub Actions - simple and reliable.

## Sibling Containers Architecture

### What Are Sibling Containers?

Instead of running Docker inside Docker (complex), we mount the host's Docker socket into our app container. This lets the app create "sibling" containers on the same Docker daemon.

```
Docker Host (EC2)
├── App Container (our platform)
│   └── /var/run/docker.sock (mounted)
└── Execution Containers (created by app)
    ├── python-eval-001
    ├── python-eval-002
    └── nodejs-eval-003
```

### Implementation

```bash
# Run app container with Docker socket mounted
docker run \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /home/ubuntu/storage:/app/storage \
  -p 8080:8080 \
  crucible:latest
```

Inside the app container:
```python
import docker

# This connects to the host's Docker daemon
client = docker.from_env()

# Creates a sibling container (not a child)
container = client.containers.run(
    'python:3.11-slim',
    command=['python', '-c', user_code],
    remove=True,
    network_mode='none',
    mem_limit='100m'
)
```

### Benefits of Sibling Containers

1. **Simpler than Docker-in-Docker**: No nested Docker daemons
2. **Better Performance**: Direct access to host Docker
3. **Standard Pattern**: Used by Jenkins, GitLab CI, etc.
4. **Same Security Model**: Execution containers still isolated

### Security Considerations

- App container has Docker access (can create/destroy containers)
- Limit app container capabilities
- Use read-only root filesystem where possible
- Monitor Docker socket access

## Current vs Future Architecture

### Phase 1: Monolithic Container (Current - Day 1)

Single container running all components:

```dockerfile
FROM python:3.11-slim

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . /app
WORKDIR /app

# Run the monolithic app
CMD ["python", "app.py", "--port", "8080"]
```

```yaml
# docker-compose.yml for local development
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./storage:/app/storage
    environment:
      - AWS_REGION=us-west-2
```

### Phase 2: Microservices Architecture (Future)

Separate containers for each component:

```yaml
# docker-compose.yml for microservices
version: '3.8'

services:
  frontend:
    image: crucible-frontend:latest
    ports:
      - "3000:3000"
    depends_on:
      - api

  api:
    image: crucible-api:latest
    ports:
      - "8080:8080"
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

  worker:
    image: crucible-worker:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - storage:/app/storage
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    deploy:
      replicas: 3  # Multiple workers

  flower:
    image: crucible-worker:latest
    command: celery flower
    ports:
      - "5555:5555"
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

volumes:
  redis-data:
  storage:
```

### Migration Path

1. **Day 1**: Containerize monolith with sibling container support
2. **Day 3**: Add Redis/Celery but keep in same container
3. **Day 4**: Deploy monolith to Kubernetes
4. **Future**: Split into microservices when needed

## Dockerfile Best Practices

### Multi-stage Build (Recommended)

```dockerfile
# Build stage
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim
WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application
COPY . .

# Ensure scripts are on PATH
ENV PATH=/root/.local/bin:$PATH

# Security: Run as non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "app.py"]
```

### Development vs Production

```dockerfile
# Development additions
FROM base as development
RUN pip install --user pytest ipython
CMD ["python", "app.py", "--debug"]

# Production
FROM base as production
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]
```

## Local Development Workflow

1. **Build locally**:
   ```bash
   docker build -t crucible:local .
   ```

2. **Run with docker-compose**:
   ```bash
   docker-compose up
   ```

3. **Test execution**:
   ```bash
   curl -X POST http://localhost:8080/api/eval \
     -H "Content-Type: application/json" \
     -d '{"code": "print(\"Hello from Docker!\")"}'
   ```

4. **Watch logs**:
   ```bash
   docker-compose logs -f
   ```

## systemd Service for Docker

```ini
# /etc/systemd/system/crucible-platform.service
[Unit]
Description=Crucible Platform Docker Container
After=docker.service
Requires=docker.service

[Service]
Type=simple
Restart=always
RestartSec=10

# Pull latest image
ExecStartPre=/usr/bin/docker pull ${ECR_URL}/crucible:latest

# Stop and remove old container
ExecStartPre=-/usr/bin/docker stop crucible-platform
ExecStartPre=-/usr/bin/docker rm crucible-platform

# Run new container
ExecStart=/usr/bin/docker run --name crucible-platform \
  --rm \
  -p 8080:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /home/ubuntu/crucible/storage:/app/storage \
  -e AWS_REGION=us-west-2 \
  ${ECR_URL}/crucible:latest

# Stop container
ExecStop=/usr/bin/docker stop crucible-platform

[Install]
WantedBy=multi-user.target
```

## Summary

- **Registry**: Amazon ECR for seamless AWS integration
- **Architecture**: Sibling containers via socket mount
- **Deployment**: systemd manages Docker container
- **Evolution**: Start with monolith, evolve to microservices
- **Trigger**: GitHub Actions triggers systemd restart after push

This approach gives us Docker benefits (consistency, portability) while keeping deployment simple and maintaining our security model for code execution.