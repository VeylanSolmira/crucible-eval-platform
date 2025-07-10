# Flower Integration Guide

## Quick Integration Steps

### 1. Update docker-compose.yml

Replace the current Flower service definition:

```yaml
# FROM THIS:
flower:
  image: mher/flower:2.0
  container_name: crucible-flower
  # ... rest of config

# TO THIS:
flower:
  build:
    context: .
    dockerfile: monitoring/flower/Dockerfile
    args:
      - BASE_IMAGE=crucible-base
  image: ${FLOWER_IMAGE:-${PROJECT_NAME:-crucible-platform}/flower:local}
  container_name: crucible-flower
  # ... rest of config (keep the same)
```

### 2. Build and Test

```bash
# Build the new Flower image
docker compose build flower

# Restart Flower
docker compose up -d flower

# Verify it's working
curl -u admin:changeme http://localhost:5555/healthcheck
```

### 3. Verify Full Functionality

1. Navigate to http://localhost:5555
2. Check that these tabs now work:
   - **Tasks**: Should show full task details
   - **Workers**: Should display celery@<container-id>
   - **Broker**: Should show Redis queue info

### 4. Update Documentation

Once confirmed working, update `/docs/demos/monitoring-demo.md` to remove the 404 warnings and document the full functionality.

## What This Fixes

- **Before**: Generic Flower image without access to task definitions
- **After**: Custom Flower image that can introspect our Celery app
- **Result**: Full monitoring UI functionality

## Rollback Plan

If issues arise, simply revert the docker-compose.yml change and rebuild:
```bash
git checkout docker-compose.yml
docker compose up -d flower
```