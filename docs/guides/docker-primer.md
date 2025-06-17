# Docker Primer: Architecture, Commands, and Best Practices

## Table of Contents
1. [What is Docker?](#what-is-docker)
2. [Core Concepts](#core-concepts)
3. [Architecture](#architecture)
4. [Essential Commands](#essential-commands)
5. [Dockerfile Deep Dive](#dockerfile-deep-dive)
6. [Docker Compose](#docker-compose)
7. [Networking](#networking)
8. [Storage and Volumes](#storage-and-volumes)
9. [Security Best Practices](#security-best-practices)
10. [Debugging and Troubleshooting](#debugging-and-troubleshooting)

## What is Docker?

Docker is a platform for developing, shipping, and running applications in containers. Containers package an application with all its dependencies into a standardized unit for software development.

### Key Benefits
- **Consistency**: Same environment everywhere (dev, staging, production)
- **Isolation**: Applications run in isolated environments
- **Portability**: Run anywhere Docker is installed
- **Efficiency**: Lighter than VMs, share host OS kernel
- **Scalability**: Easy to scale up/down

## Core Concepts

### Images
- **Definition**: Read-only templates containing application code, runtime, libraries, and dependencies
- **Layers**: Images are built in layers, each instruction creates a new layer
- **Registry**: Images are stored in registries (Docker Hub, ECR, etc.)

### Containers
- **Definition**: Running instances of images
- **Lifecycle**: Created from images, can be started, stopped, moved, deleted
- **Isolation**: Each container runs in isolation but can communicate through defined channels

### Dockerfile
- **Definition**: Text file with instructions to build an image
- **Instructions**: FROM, RUN, COPY, CMD, etc.

### Registry
- **Docker Hub**: Default public registry
- **Private Registries**: ECR, GCR, Azure Container Registry, self-hosted

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Client (CLI)                      │
│                   docker build, run, pull                    │
└─────────────────────┬───────────────────────────────────────┘
                      │ REST API
┌─────────────────────▼───────────────────────────────────────┐
│                     Docker Daemon                            │
│                      (dockerd)                               │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────┐  │
│  │   Images    │  │ Containers  │  │     Networks      │  │
│  └─────────────┘  └─────────────┘  └───────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────┐  │
│  │   Volumes   │  │   Plugins   │  │   Build Cache     │  │
│  └─────────────┘  └─────────────┘  └───────────────────┘  │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 Container Runtime (containerd)               │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    Linux Kernel                              │
│          (namespaces, cgroups, union filesystem)            │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Docker Client**: CLI tool that users interact with
2. **Docker Daemon**: Background service managing Docker objects
3. **Container Runtime**: Low-level runtime (containerd/runc)
4. **Storage Driver**: Manages image layers and container storage

## Essential Commands

### Image Management

```bash
# Pull an image from registry
docker pull python:3.11-slim

# List images
docker images
docker image ls

# Build an image
docker build -t myapp:latest .
docker build -f custom.Dockerfile -t myapp:v2 .

# Remove images
docker rmi myapp:latest
docker image prune  # Remove unused images

# Tag an image
docker tag myapp:latest myregistry.com/myapp:latest

# Push to registry
docker push myregistry.com/myapp:latest
```

### Container Management

```bash
# Run a container
docker run nginx
docker run -d -p 8080:80 --name webserver nginx
docker run -it ubuntu bash

# List containers
docker ps          # Running containers
docker ps -a       # All containers

# Stop/Start/Restart
docker stop webserver
docker start webserver
docker restart webserver

# Remove containers
docker rm webserver
docker container prune  # Remove stopped containers

# Execute commands in running container
docker exec -it webserver bash
docker exec webserver ls /var/www

# View logs
docker logs webserver
docker logs -f webserver  # Follow logs

# Inspect container
docker inspect webserver
docker stats  # Live resource usage
```

### System Management

```bash
# System information
docker info
docker version

# Clean up everything
docker system prune
docker system prune -a --volumes  # Remove everything unused

# View disk usage
docker system df
```

## Dockerfile Deep Dive

### Multi-stage Builds

```dockerfile
# Build stage - compile/build artifacts
FROM golang:1.19 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o myapp

# Runtime stage - minimal final image
FROM alpine:3.17
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/myapp .
CMD ["./myapp"]
```

### Best Practices

```dockerfile
# 1. Use specific tags, not latest
FROM python:3.11-slim

# 2. Set working directory
WORKDIR /app

# 3. Copy dependency files first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy application code
COPY . .

# 5. Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 6. Use ENTRYPOINT for main command, CMD for default args
ENTRYPOINT ["python"]
CMD ["app.py"]

# 7. Add health checks
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:8080/health || exit 1

# 8. Use .dockerignore to exclude files
# 9. Minimize layers - combine RUN commands
# 10. Clean up in same layer
RUN apt-get update && \
    apt-get install -y package && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```

### Dockerfile Instructions

| Instruction | Purpose | Example |
|------------|---------|---------|
| FROM | Base image | `FROM python:3.11` |
| RUN | Execute commands | `RUN apt-get update` |
| COPY | Copy files from host | `COPY . /app` |
| ADD | Copy files (with extraction) | `ADD archive.tar.gz /` |
| WORKDIR | Set working directory | `WORKDIR /app` |
| ENV | Set environment variables | `ENV PORT=8080` |
| EXPOSE | Document exposed ports | `EXPOSE 8080` |
| USER | Set user | `USER appuser` |
| CMD | Default command | `CMD ["python", "app.py"]` |
| ENTRYPOINT | Main command | `ENTRYPOINT ["python"]` |
| ARG | Build arguments | `ARG VERSION=latest` |
| LABEL | Add metadata | `LABEL version="1.0"` |
| VOLUME | Declare volumes | `VOLUME /data` |

## Docker Compose

### Basic docker-compose.yml

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DB_HOST=postgres
    depends_on:
      - postgres
    volumes:
      - ./app:/app
      - app-data:/data
    networks:
      - backend

  postgres:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: secret
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - backend

networks:
  backend:

volumes:
  app-data:
  postgres-data:
```

### Compose Commands

```bash
# Start services
docker-compose up
docker-compose up -d  # Detached

# Stop services
docker-compose down
docker-compose down -v  # Remove volumes too

# View logs
docker-compose logs
docker-compose logs -f web

# Execute commands
docker-compose exec web bash

# Scale services
docker-compose up -d --scale web=3

# Build/rebuild
docker-compose build
docker-compose up --build

# Restart services
docker-compose restart                    # Restart all services
docker-compose restart web               # Restart specific service
docker-compose restart -t 30             # With 30s timeout

# Force recreate containers
docker-compose up -d --force-recreate    # Recreate even if config unchanged
docker-compose up -d --build --force-recreate  # Rebuild and recreate

# Apply configuration changes
docker-compose up -d                     # Automatically recreates changed services
```

## Networking

### Network Types

1. **Bridge** (default): Isolated network for containers
2. **Host**: Use host's network directly
3. **None**: No networking
4. **Overlay**: Multi-host networking (Swarm)
5. **Macvlan**: Assign MAC addresses

### Network Commands

```bash
# List networks
docker network ls

# Create network
docker network create mynet

# Connect container
docker run -d --network mynet --name web nginx
docker network connect mynet existing-container

# Inspect network
docker network inspect mynet

# Disconnect
docker network disconnect mynet web
```

### Container Communication

```bash
# Containers on same network can communicate by name
docker run -d --network mynet --name db postgres
docker run -d --network mynet --name web -e DB_HOST=db myapp
```

## Storage and Volumes

### Volume Types

1. **Named Volumes**: Managed by Docker
2. **Bind Mounts**: Map host directory
3. **tmpfs**: Memory-only (Linux)

### Volume Commands

```bash
# Create volume
docker volume create mydata

# List volumes
docker volume ls

# Inspect volume
docker volume inspect mydata

# Use volumes
docker run -v mydata:/data myapp              # Named volume
docker run -v /host/path:/container/path myapp # Bind mount
docker run --mount source=mydata,target=/data myapp # New syntax

# Remove volumes
docker volume rm mydata
docker volume prune
```

### Volume Best Practices

```yaml
# docker-compose.yml
services:
  app:
    volumes:
      # Named volume for data persistence
      - app-data:/var/lib/app
      # Bind mount for development
      - ./src:/app/src:ro
      # Config file
      - ./config.yml:/app/config.yml:ro

volumes:
  app-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/app
```

## Security Best Practices

### 1. Use Non-Root Users

```dockerfile
RUN useradd -m -u 1000 appuser
USER appuser
```

### 2. Scan Images

```bash
# Using Docker Scout
docker scout cves myapp:latest

# Using Trivy
trivy image myapp:latest
```

### 3. Security Options

```yaml
# docker-compose.yml
services:
  app:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
```

### 4. Secrets Management

```bash
# Create secret
echo "mypassword" | docker secret create db_pass -

# Use in compose
services:
  app:
    secrets:
      - db_pass
secrets:
  db_pass:
    external: true
```

### 5. Image Signing

```bash
# Enable content trust
export DOCKER_CONTENT_TRUST=1

# Sign images
docker trust sign myregistry/myapp:latest
```

## Debugging and Troubleshooting

### Container Debugging

```bash
# Get container details
docker inspect container_name

# View processes
docker top container_name

# Resource usage
docker stats container_name

# Export filesystem
docker export container_name > container.tar

# Copy files
docker cp container_name:/path/to/file ./local/path

# Debug networking
docker run --rm --network container:target_container nicolaka/netshoot
```

### Image Debugging

```bash
# View image layers
docker history myapp:latest

# Inspect image
docker inspect myapp:latest

# Extract image filesystem
docker save myapp:latest | tar -xv

# Dive tool for layer analysis
dive myapp:latest
```

### Common Issues and Solutions

1. **Container exits immediately**
   ```bash
   # Check exit code and logs
   docker ps -a
   docker logs container_name
   ```

2. **Permission denied**
   ```bash
   # Check user and file permissions
   docker exec container_name id
   docker exec container_name ls -la /problem/path
   ```

3. **Cannot connect to container**
   ```bash
   # Check port mapping
   docker port container_name
   netstat -tlnp | grep 8080
   ```

4. **Disk space issues**
   ```bash
   docker system df
   docker system prune -a
   ```

5. **Build cache issues**
   ```bash
   docker build --no-cache -t myapp .
   ```

### Docker Daemon Debugging

```bash
# View daemon logs
journalctl -u docker.service

# Debug mode
dockerd --debug

# API debugging
docker -D info
```

## Advanced Topics

### Docker in Docker (DinD) vs Docker Outside Docker (DooD)

**DinD**: Running Docker daemon inside container
```bash
docker run --privileged -d docker:dind
```

**DooD** (Sibling Containers): Mount host's Docker socket
```bash
docker run -v /var/run/docker.sock:/var/run/docker.sock myapp
```

### BuildKit (Modern Build System)

```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1

# Use build secrets
docker build --secret id=npm,src=$HOME/.npmrc .

# In Dockerfile
RUN --mount=type=secret,id=npm,target=/root/.npmrc npm install
```

### Container Registries

```bash
# Docker Hub
docker login
docker push username/image:tag

# AWS ECR
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URL
docker tag myapp:latest $ECR_URL/myapp:latest
docker push $ECR_URL/myapp:latest

# Self-hosted
docker run -d -p 5000:5000 --name registry registry:2
docker tag myapp localhost:5000/myapp
docker push localhost:5000/myapp
```

## Summary

Docker revolutionizes application deployment by providing consistent, isolated environments. Key takeaways:

1. **Images are templates, containers are instances**
2. **Use multi-stage builds for smaller images**
3. **Always run as non-root user**
4. **Leverage build cache with proper layer ordering**
5. **Use volumes for persistent data**
6. **Network isolation by default, explicit connections**
7. **Regular cleanup prevents disk issues**
8. **Security scanning is essential**

This primer covers the essentials, but Docker is a vast ecosystem. Continue exploring orchestration (Kubernetes), CI/CD integration, and advanced networking for production deployments.