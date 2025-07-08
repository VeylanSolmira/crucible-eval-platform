# Docker Compose Build Separation - Professional Approach

## Current State (Pragmatic Solution)

We're using busybox placeholder images in production to avoid "pull access denied" warnings:
```yaml
# docker-compose.prod.yml
base:
  image: busybox:latest
  command: "true"
```

This works but mixes build and runtime concerns in the same file.

## Professional Solution: Separate Build Composition

### Structure
```
docker-compose.yml          # Runtime services only
docker-compose.build.yml    # Build definitions only
docker-compose.override.yml # Local dev overrides (optional)
docker-compose.prod.yml     # Production overrides
```

### Implementation

**docker-compose.yml** (runtime only):
```yaml
services:
  api-service:
    image: ${API_IMAGE:-crucible-platform/api:latest}
    # NO build: section
    depends_on:
      - postgres
      - redis
    # ... rest of runtime config
```

**docker-compose.build.yml** (build only):
```yaml
services:
  base:
    image: crucible-base
    build:
      context: .
      dockerfile: shared/docker/base.Dockerfile
  
  api-service:
    build:
      context: .
      dockerfile: api/Dockerfile
      args:
        BASE_IMAGE: crucible-base
    depends_on:
      - base
```

### Usage

**Local Development:**
```bash
# Build everything
docker compose -f docker-compose.yml -f docker-compose.build.yml build

# Run services
docker compose up -d
```

**CI/CD Pipeline:**
```bash
# Build and push
docker compose -f docker-compose.yml -f docker-compose.build.yml build
docker compose -f docker-compose.yml -f docker-compose.build.yml push
```

**Production:**
```bash
# Just pull and run (no build files needed)
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Benefits

1. **Clear Separation**: Build-time vs runtime concerns
2. **No Warnings**: Production doesn't know about build services
3. **Flexibility**: Can build without running, run without building
4. **Security**: Production systems don't need build tools
5. **Professional**: Standard practice in enterprise environments

### Migration Path

1. Create `docker-compose.build.yml` with all build configurations
2. Remove `build:` sections from `docker-compose.yml`
3. Update scripts to use both files when building
4. Test all workflows (dev, CI/CD, prod)
5. Remove busybox workarounds from prod override

This is the pattern used by companies like Netflix, Spotify, and most enterprises using Docker Compose at scale.