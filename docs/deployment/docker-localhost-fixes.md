# Docker Localhost Configuration Fixes

## Changes Made for Docker Deployment

### 1. Frontend Binding Address
**File**: `src/web_frontend/web_frontend.py`
- Changed `host: str = "localhost"` to `host: str = "0.0.0.0"`
- This allows the container to accept connections from the host

### 2. Service Registry
**File**: `src/shared/service_registry.py`
- Added environment-aware host configuration
- Uses `crucible` service name when `IN_DOCKER=true`
- Falls back to `localhost` for local development

### 3. Docker Compose Environment
**File**: `docker-compose.yml`
- Added `IN_DOCKER=true` environment variable
- This triggers the service registry to use Docker service names

### 4. Platform Host Configuration
**File**: `src/web_frontend/web_frontend.py`
- Made `platform_host` configurable via `PLATFORM_HOST` environment variable
- Defaults to `localhost` if not set

### 5. Display Messages
**File**: `app.py`
- Updated startup message to show `http://0.0.0.0:8080`
- More accurate representation of the bind address

## Testing the Changes

1. **Rebuild the container**:
   ```bash
   docker compose down
   docker compose build --no-cache
   docker compose up -d
   ```

2. **Check container is running**:
   ```bash
   docker ps | grep crucible
   ```

3. **View logs**:
   ```bash
   docker logs crucible-platform -f
   ```

4. **Test connection**:
   ```bash
   curl http://localhost:8080
   ```

## Troubleshooting

If still having connection issues:

1. **Check port availability**:
   ```bash
   lsof -i :8080
   ```

2. **Test container internally**:
   ```bash
   docker exec crucible-platform curl http://localhost:8080
   ```

3. **Check Docker networking**:
   ```bash
   docker network ls
   docker port crucible-platform
   ```

4. **Restart Docker Desktop** (if on macOS/Windows)

## Why These Changes Matter

- **Container Isolation**: Containers have their own network namespace
- **localhost Inside Container**: Only accessible within that container
- **0.0.0.0 Binding**: Makes the service accessible through Docker's port mapping
- **Service Names**: In Docker Compose, services can reach each other by name