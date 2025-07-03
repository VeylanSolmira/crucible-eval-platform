# Docker BuildKit Optimization Guide

## Overview

Docker BuildKit is a next-generation build subsystem that significantly improves build performance, especially for multi-stage, multi-service architectures like ours.

## Why BuildKit Helps

### 1. **Parallel Layer Building**
Traditional Docker builds execute Dockerfile instructions sequentially. BuildKit can run independent build stages in parallel:

```dockerfile
# These stages can build simultaneously with BuildKit
FROM node:18 AS frontend-deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM python:3.11 AS backend-deps
WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt

FROM python:3.11 AS final
# Merge results from parallel stages
COPY --from=backend-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=frontend-deps /app/node_modules /app/node_modules
```

### 2. **Smarter Caching**
BuildKit has more intelligent cache management:
- **Remote cache**: Can pull/push cache from registries
- **Inline cache**: Embeds cache metadata in images
- **Cache mounts**: Persistent caches for package managers

```dockerfile
# Cache mount example - npm cache persists between builds
RUN --mount=type=cache,target=/root/.npm \
    npm ci --cache /root/.npm

# Python pip cache
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
```

### 3. **Skip Unused Stages**
BuildKit only builds stages that are actually needed:

```dockerfile
FROM python:3.11 AS dev
# Development dependencies
RUN pip install pytest black mypy

FROM python:3.11 AS prod
# Production only
RUN pip install gunicorn

# BuildKit skips 'dev' stage when building for prod
FROM prod AS final
```

### 4. **Better Build Context Transfer**
- Only sends files actually used in the build
- Can exclude files more efficiently
- Supports `.dockerignore` patterns better
- Can use remote Git repositories as context

### 5. **Concurrent Operations**
BuildKit can:
- Download multiple base images simultaneously
- Run multiple RUN commands in parallel (when safe)
- Process COPY operations concurrently
- Build multiple independent stages at once

### 6. **Real Performance Example**
For our multi-service setup:

```yaml
# Without BuildKit: Sequential
1. Build base image (2 min)
2. Build API (1 min)  
3. Build frontend (3 min)
4. Build worker (1 min)
Total: 7 minutes

# With BuildKit: Parallel where possible
1. Build base image (2 min)
2. Build API + frontend + worker in parallel (3 min - limited by slowest)
Total: 5 minutes (30% faster!)
```

## Enabling BuildKit

### For Docker Compose

```bash
# Option 1: Environment variables (recommended)
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
docker-compose build

# Option 2: Inline
DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 docker-compose build
```

### For Docker CLI

```bash
# Option 1: Environment variable
export DOCKER_BUILDKIT=1
docker build .

# Option 2: Docker daemon config
# Edit /etc/docker/daemon.json
{
  "features": {
    "buildkit": true
  }
}
```

### In CI/CD (GitHub Actions)

```yaml
- name: Build with BuildKit
  env:
    DOCKER_BUILDKIT: 1
    COMPOSE_DOCKER_CLI_BUILD: 1
  run: docker-compose build --parallel
```

## BuildKit-Specific Features

### 1. **Cache Mounts**
Persist package manager caches between builds:

```dockerfile
# Python pip cache
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Node.js npm cache
RUN --mount=type=cache,target=/root/.npm \
    npm ci --cache /root/.npm

# APT cache
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    apt-get update && apt-get install -y build-essential
```

### 2. **Secret Mounts**
Securely use secrets during build without storing in image:

```dockerfile
# Use secret during build only
RUN --mount=type=secret,id=github_token \
    pip install git+https://$(cat /run/secrets/github_token)@github.com/org/private-repo.git
```

### 3. **SSH Mounts**
Use SSH keys during build:

```dockerfile
RUN --mount=type=ssh \
    git clone git@github.com:org/private-repo.git
```

### 4. **Bind Mounts**
Mount directories from build context:

```dockerfile
RUN --mount=type=bind,source=.,target=/context \
    cp /context/configs/* /app/configs/
```

## Optimizing Our Dockerfiles

### Current Base Image
```dockerfile
FROM python:3.11-slim AS base
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*
```

### Optimized with BuildKit
```dockerfile
FROM python:3.11-slim AS base
WORKDIR /app

# Use cache mount for apt
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Cache mount for pip
COPY requirements-base.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements-base.txt
```

### Parallel Service Builds
```yaml
# docker-compose.yml with proper dependencies
services:
  base:
    build:
      context: .
      dockerfile: Dockerfile.base
  
  api:
    build:
      context: .
      dockerfile: api/Dockerfile
      cache_from:
        - ${REGISTRY}/crucible-base:latest
    depends_on:
      - base
  
  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
      # Frontend can build independently!
  
  worker:
    build:
      context: .
      dockerfile: worker/Dockerfile
      cache_from:
        - ${REGISTRY}/crucible-base:latest
    depends_on:
      - base
```

## Performance Monitoring

### Build Time Comparison
```bash
# Without BuildKit
time docker-compose build
# real    7m32s

# With BuildKit
time DOCKER_BUILDKIT=1 docker-compose build --parallel
# real    5m12s (31% faster!)
```

### Viewing Build Performance
BuildKit provides detailed timing for each step:

```
#12 [stage-1 3/8] RUN pip install -r requirements.txt
#12 0.542 Collecting fastapi==0.104.1
#12 1.234 Downloading fastapi-0.104.1-py3-none-any.whl (92 kB)
#12 DONE 3.2s
```

## Best Practices

1. **Order Dockerfile instructions by change frequency**
   - Static dependencies first
   - Application code last

2. **Use multi-stage builds**
   - Separate build and runtime dependencies
   - Smaller final images

3. **Leverage cache mounts**
   - Especially for package managers
   - Speeds up rebuilds significantly

4. **Set up CI caching**
   - Use registry caching
   - Share cache between CI runs

5. **Monitor build performance**
   - Use `--progress=plain` for detailed output
   - Identify bottlenecks

## Troubleshooting

### BuildKit Not Working?
```bash
# Check if enabled
docker version | grep -i buildkit

# Force enable
export DOCKER_BUILDKIT=1

# Check Docker daemon
docker info | grep -i buildkit
```

### Cache Issues?
```bash
# Clear BuildKit cache
docker builder prune

# Clear all build cache
docker builder prune -a
```

## Conclusion

For our platform with 10+ services, BuildKit can reduce build times by 30-50% through:
- Parallel stage execution
- Smarter caching
- Skipping unused stages
- Better resource utilization

Enable it today for faster development cycles!