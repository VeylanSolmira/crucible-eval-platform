# Base Executor Image

This is the base executor image for the Crucible platform. It provides a minimal Python environment for secure code execution.

## Security Model

The image itself is minimal - security is enforced by the executor service when creating containers:

### Container Runtime Restrictions
- **Network**: `--network=none` (complete isolation)
- **Filesystem**: `--read-only` (except /tmp)
- **Memory**: 512MB limit
- **CPU**: 0.5 CPU limit
- **Privileges**: `--security-opt=no-new-privileges:true`
- **Temporary Storage**: 100MB tmpfs at /tmp

### Image Design
- Based on `python:3.11-slim` for minimal size
- Non-root user (`executor`) for defense in depth
- No package managers (pip, apt) in final image
- No build tools or compilers
- Minimal attack surface

## Usage

This image is used by the executor-service. It's not meant to be run directly.

The executor service creates containers from this image with:
```python
container = docker_client.containers.create(
    image="executor-base:latest",  # This image
    command=["python", "-c", user_code],
    # ... security restrictions ...
)
```

## Building

```bash
docker build -t executor-base:latest .
```

## Future Enhancements

For production:
- Consider distroless base images
- Add security scanning in CI/CD
- Implement image signing
- Use read-only root filesystem in image itself