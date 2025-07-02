# Container Deployment Strategies for Crucible Platform

## Overview

This document explores different strategies for running containers on EC2, with specific consideration for where to run the Nginx reverse proxy.

## Current Architecture

```
EC2 Host
├── Docker Engine
├── Docker Compose
│   ├── crucible-platform (backend)
│   ├── crucible-frontend (React)
│   └── postgres (database)
└── Nginx (proposed on host)
```

## Nginx Deployment Options

### Option 1: Nginx on Host (Current Plan)

```yaml
# On EC2 host directly
EC2 Host
├── Nginx (apt-get install nginx)
│   ├── Handles SSL termination
│   ├── Reverse proxy to containers
│   └── Rate limiting
└── Docker Compose Stack
```

**Pros:**
- One less container to manage
- Easier SSL certificate management with certbot
- Can serve error pages even if Docker is down
- System-level integration (systemd)

**Cons:**
- Inconsistent with container philosophy
- Configuration drift between environments
- Manual updates required
- Not portable

### Option 2: Nginx in Container (Recommended)

```yaml
# docker-compose.yml addition
services:
  nginx:
    image: nginx:alpine
    container_name: crucible-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - certbot-etc:/etc/letsencrypt
      - certbot-var:/var/lib/letsencrypt
    depends_on:
      - crucible-platform
      - crucible-frontend
    restart: unless-stopped

  certbot:
    image: certbot/certbot
    volumes:
      - certbot-etc:/etc/letsencrypt
      - certbot-var:/var/lib/letsencrypt
      - ./data/certbot/www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
```

**Pros:**
- Consistent containerized architecture
- Version controlled Nginx config
- Portable across environments
- Easy rollback
- Can test locally

**Cons:**
- Slightly more complex certificate management
- Need to handle container networking
- Additional container overhead (minimal)

### Option 3: Nginx as Sidecar Pattern

```yaml
# Each service gets its own Nginx
services:
  backend-proxy:
    image: nginx:alpine
    volumes:
      - ./nginx/backend.conf:/etc/nginx/nginx.conf:ro
    # Routes only to backend
    
  frontend-proxy:
    image: nginx:alpine
    volumes:
      - ./nginx/frontend.conf:/etc/nginx/nginx.conf:ro
    # Routes only to frontend
```

**Pros:**
- Service isolation
- Independent scaling
- Per-service configuration

**Cons:**
- More complex
- Multiple SSL termination points
- Harder to manage

## Container Orchestration Strategies

### 1. Docker Compose on EC2 (Current)

**Best for:** Development, small deployments, rapid iteration

```bash
# Simple deployment
docker-compose up -d
docker-compose ps
docker-compose logs
```

### 2. ECS with EC2 Launch Type

**Best for:** Production AWS deployments with Docker-in-Docker needs

```json
{
  "family": "crucible-platform",
  "taskDefinition": {
    "containerDefinitions": [
      {
        "name": "nginx",
        "image": "nginx:alpine",
        "portMappings": [{"containerPort": 80}],
        "links": ["backend", "frontend"]
      },
      {
        "name": "backend",
        "image": "crucible-platform:latest",
        "mountPoints": [{
          "sourceVolume": "docker-socket",
          "containerPath": "/var/run/docker.sock"
        }]
      }
    ]
  }
}
```

### 3. ECS Fargate (Serverless)

**Best for:** Microservices without Docker-in-Docker

```yaml
# Cannot mount Docker socket
# Would need to redesign execution strategy
```

### 4. Kubernetes (EKS)

**Best for:** Large scale, multi-cloud, complex orchestration

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crucible-platform
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
      - name: backend
        image: crucible-platform:latest
```

## Recommendation Path

### Phase 1: Current Sprint (Keep Simple)
- Continue with Nginx on host for now
- Get HTTPS working quickly
- Focus on core functionality

### Phase 2: Containerize Nginx (Next Week)
```yaml
# Add to docker-compose.yml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx/conf:/etc/nginx/conf.d:ro
    - certbot-etc:/etc/letsencrypt
    - certbot-www:/var/www/certbot
```

### Phase 3: Production Migration
- Move to ECS for orchestration
- Keep EC2 launch type for Docker socket access
- Use Application Load Balancer for SSL

## Implementation Notes

### Containerized Nginx Configuration

1. **Directory Structure:**
```
/home/ubuntu/crucible/
├── docker-compose.yml
├── nginx/
│   ├── conf.d/
│   │   └── crucible.conf
│   ├── nginx.conf
│   └── ssl/ (if manual certs)
└── data/
    └── certbot/
```

2. **Certificate Management with Containerized Nginx:**
```bash
# Initial certificate
docker-compose run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  -d crucible.veylan.dev

# Auto-renewal via container
# Already handled by certbot container entrypoint
```

3. **Zero-Downtime Nginx Updates:**
```bash
# Update config
vim nginx/conf.d/crucible.conf

# Test configuration
docker-compose exec nginx nginx -t

# Reload without downtime
docker-compose exec nginx nginx -s reload
```

## Decision Matrix

| Factor | Nginx on Host | Nginx in Container | Winner |
|--------|--------------|-------------------|---------|
| Consistency | ❌ | ✅ | Container |
| Simplicity | ✅ | ❌ | Host |
| Portability | ❌ | ✅ | Container |
| Certificate Mgmt | ✅ | ➖ | Host |
| Version Control | ❌ | ✅ | Container |
| Local Testing | ❌ | ✅ | Container |
| Production Ready | ➖ | ✅ | Container |

## Conclusion

While Nginx on the host is simpler for initial setup, containerizing Nginx aligns better with modern practices and our overall architecture. The recommendation is:

1. **For immediate needs:** Proceed with Nginx on host to get HTTPS working
2. **Next iteration:** Migrate Nginx to container with proper volume mounts
3. **Production:** Full container orchestration with ECS or Kubernetes

This approach balances pragmatism with architectural consistency.