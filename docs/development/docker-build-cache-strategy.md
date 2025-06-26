# Docker Build Cache Strategy Guide

## Overview
Docker build cache can quickly grow to consume significant disk space. This guide covers strategies for managing build cache effectively, both generally and specifically for the Crucible platform.

## Understanding Docker Build Cache

### What Creates Build Cache?
1. **Layer Caching**: Each instruction in a Dockerfile creates a layer
2. **BuildKit Cache**: Modern builder stores intermediate build artifacts
3. **Multi-stage Builds**: Each stage creates cache entries
4. **Package Managers**: npm, pip, apt-get downloads

### Why Cache Grows Large
- Frequent rebuilds with code changes
- Multiple branches/versions being built
- Large dependencies (node_modules, Python packages)
- Unused old layers not garbage collected

## General Docker Cache Management Strategies

### 1. Regular Cleanup Commands

```bash
# View cache usage
docker system df

# Clean all unused build cache
docker builder prune -f

# Clean cache older than 24 hours
docker builder prune -f --filter until=24h

# Clean everything unused (aggressive)
docker system prune -a -f --volumes

# Clean with size limit
docker builder prune -f --keep-storage 10GB
```

### 2. Dockerfile Optimization

#### Order Dependencies by Change Frequency
```dockerfile
# Good: Less frequently changed items first
FROM node:20-alpine

# System dependencies (rarely change)
RUN apk add --no-cache python3 make g++

# Package files (change occasionally)
COPY package*.json ./
RUN npm ci

# Application code (changes frequently)
COPY . .
RUN npm run build
```

#### Use Specific COPY Commands
```dockerfile
# Bad: Copies everything, invalidates cache on any file change
COPY . .

# Good: Copy only what's needed
COPY package*.json ./
RUN npm ci
COPY src/ ./src/
COPY public/ ./public/
RUN npm run build
```

#### Leverage .dockerignore
```dockerignore
# .dockerignore
node_modules
.git
*.log
.env
coverage
.nyc_output
dist
build
.cache
*.md
```

### 3. Multi-stage Build Optimization

```dockerfile
# Dependencies stage (cached when package.json unchanged)
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

# Builder stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# Final stage (minimal size)
FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=builder /app/dist ./dist
CMD ["node", "dist/index.js"]
```

### 4. BuildKit Cache Mount

```dockerfile
# Use cache mount for package managers
RUN --mount=type=cache,target=/root/.npm \
    npm ci

# Python example
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
```

### 5. Build Cache Export/Import

```bash
# Export cache to registry
docker buildx build \
  --cache-to type=registry,ref=myregistry/myapp:buildcache \
  --cache-from type=registry,ref=myregistry/myapp:buildcache \
  .

# Export cache to local directory
docker buildx build \
  --cache-to type=local,dest=/tmp/docker-cache \
  --cache-from type=local,src=/tmp/docker-cache \
  .
```

## Crucible-Specific Strategies

### 1. Service-Specific .dockerignore

Create service-specific .dockerignore files:

```bash
# frontend/.dockerignore
node_modules
.next
coverage
*.log
.env.local

# api/.dockerignore
__pycache__
*.pyc
.pytest_cache
.coverage
venv
```

### 2. Shared Base Images

```dockerfile
# base.Dockerfile
FROM python:3.11-slim AS python-base
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Use in services
FROM crucible-base:latest
# Service-specific build
```

### 3. Development vs Production Builds

```yaml
# docker-compose.yml
services:
  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
      target: ${BUILD_TARGET:-runner}  # dev or runner
      cache_from:
        - crucible-platform-frontend:cache
```

### 4. Automated Cache Management

```yaml
# .github/workflows/cleanup.yml
name: Docker Cache Cleanup
on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly
  workflow_dispatch:

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - name: Clean Docker Cache
        run: |
          docker builder prune -f --filter until=168h
          docker system prune -f --filter until=168h
```

### 5. Layer Caching for CI/CD

```yaml
# GitHub Actions example
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v2

- name: Build with cache
  uses: docker/build-push-action@v4
  with:
    context: .
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

## Best Practices

### 1. Cache Invalidation Strategy
- Use hash of dependency files as cache keys
- Clear cache when major dependencies update
- Version your base images

### 2. Development Workflow
```bash
# Create aliases for common operations
alias docker-clean='docker builder prune -f --filter until=24h'
alias docker-clean-all='docker system prune -a -f --volumes'

# Use BuildKit for better caching
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
```

### 3. Monitoring Cache Size
```bash
#!/bin/bash
# monitor-cache.sh
CACHE_SIZE=$(docker system df --format json | jq '.BuildCache.Size' | numfmt --to=iec)
if [[ $(docker system df --format json | jq '.BuildCache.Size') -gt 20000000000 ]]; then
    echo "Cache size $CACHE_SIZE exceeds 20GB, cleaning..."
    docker builder prune -f --filter until=48h
fi
```

### 4. Project-Specific Configuration

```json
// .dockerbuild.json
{
  "cache_rules": {
    "max_size": "20GB",
    "prune_after_days": 7,
    "keep_tagged": true
  },
  "build_args": {
    "BUILDKIT_INLINE_CACHE": "1"
  }
}
```

## Troubleshooting

### Cache Not Being Used
```bash
# Check if BuildKit is enabled
echo $DOCKER_BUILDKIT

# Verify cache-from sources
docker buildx inspect

# Debug cache hits/misses
DOCKER_BUILDKIT=1 docker build --progress=plain .
```

### Disk Space Issues
```bash
# Find large Docker files
du -sh /var/lib/docker/*

# Check container logs size
docker ps -q | xargs docker inspect --format='{{.LogPath}}' | xargs ls -lh

# Clean everything safely
docker system prune -a --volumes -f
```

## Crucible Platform Specific Tips

### 1. Frontend (Next.js)
- Cache node_modules separately from build artifacts
- Use `.next/cache` for build cache
- Clear `.next` directory in development when switching branches

### 2. Python Services
- Use pip cache mounts
- Separate requirements.txt from requirements-dev.txt
- Cache compiled Python files carefully

### 3. Development vs CI
- Use different cache strategies for local dev vs CI
- CI can use registry-based caching
- Local development can use larger cache limits

### 4. Compose-Specific
```yaml
# docker-compose.yml
x-build-args: &build-args
  BUILDKIT_INLINE_CACHE: 1
  
services:
  frontend:
    build:
      args:
        <<: *build-args
```

## Maintenance Schedule

### Daily (Development)
- Monitor cache size with `docker system df`
- Clean if over 30GB

### Weekly
- Run `docker builder prune -f --filter until=72h`
- Check for unused images

### Monthly
- Full cleanup: `docker system prune -a -f`
- Review and update .dockerignore files
- Audit Dockerfile efficiency

## Summary

Key takeaways for Crucible platform:
1. **Use multi-stage builds** to minimize final image size
2. **Order Dockerfile instructions** by change frequency
3. **Implement regular cleanup** automation
4. **Monitor cache size** proactively
5. **Use BuildKit features** for better caching
6. **Separate concerns** between dev and production builds

Remember: A well-managed cache speeds up builds significantly, but an unmanaged cache can consume all available disk space and actually slow down builds due to cache lookup overhead.