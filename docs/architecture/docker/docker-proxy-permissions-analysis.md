# Docker Proxy Permissions Analysis

## Required Docker Operations

Based on the executor service code analysis, here are the Docker operations we perform:

### 1. Health Check (line 48)
- `docker_client.ping()` - Tests Docker connectivity
- **Required permission**: `PING` or basic connectivity

### 2. Image Operations (lines 65-69)
- `docker_client.images.get("python:3.11-slim")` - Check if image exists
- `docker_client.images.pull("python:3.11-slim")` - Pull image if not present
- **Required permissions**: 
  - `IMAGES: 1` - To check/list images
  - `POST: 1` - For the pull operation

### 3. Container Operations (lines 73-95)
- `docker_client.containers.run()` - Create and start container
- **Required permissions**:
  - `CONTAINERS: 1` - Basic container operations
  - `CONTAINERS_CREATE: 1` - Create containers
  - `POST: 1` - For create operation

### 4. Container Management (lines 99-169)
- `container.wait(timeout=timeout)` - Wait for container completion
- `container.logs()` - Get container output
- `container.stop()` - Stop container on timeout
- `container.kill()` - Force kill if stop fails
- `container.remove(force=True)` - Clean up container
- **Required permissions**:
  - `CONTAINERS_WAIT: 1` - Wait for container
  - `CONTAINERS_STOP: 1` - Stop container
  - `CONTAINERS_REMOVE: 1` - Remove container

### 5. Container Listing (lines 196-200)
- `docker_client.containers.list()` - List containers with filters
- **Required permissions**:
  - `CONTAINERS: 1` - List containers

## Permissions We DON'T Need

Based on the code analysis, we do NOT need:
- `NETWORKS: 0` - We use `network_mode="none"`, no network management
- `VOLUMES: 0` - We only use tmpfs, no volume management
- `EXEC: 0` - We never exec into containers
- `BUILD: 0` - We never build images
- `INFO: 1` - Not used in the code
- `VERSION: 1` - Not used in the code
- `IMAGES_PULL: 1` - This might not be a valid permission

## Minimal Required Permissions

```yaml
docker-proxy:
  environment:
    # Container operations
    CONTAINERS: 1         # List containers
    CONTAINERS_CREATE: 1  # Create containers
    CONTAINERS_START: 1   # Start containers (implicit in run)
    CONTAINERS_STOP: 1    # Stop containers on timeout
    CONTAINERS_WAIT: 1    # Wait for completion
    CONTAINERS_REMOVE: 1  # Cleanup
    # Image operations
    IMAGES: 1            # Check if image exists
    # Required for create/pull operations
    POST: 1              # HTTP POST method
    # Explicitly deny everything else
    EXEC: 0
    VOLUMES: 0
    NETWORKS: 0
    BUILD: 0
    INFO: 0
    VERSION: 0
```

## Testing Strategy

1. Remove INFO and VERSION permissions
2. Test if IMAGES_PULL is a valid permission or if POST covers it
3. Verify each operation with minimal permissions
4. Document any additional permissions needed for edge cases

## Security Notes

- The executor explicitly sets `network_mode="none"` for isolation
- Uses read-only root filesystem with tmpfs for /tmp
- Sets memory and CPU limits
- Uses security options like no-new-privileges
- This is a good security posture for untrusted code execution