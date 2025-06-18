# Docker Dev/Prod Parity Guide

## The Problem

Docker behaves differently on macOS (Docker Desktop) vs Linux (native Docker):

1. **Path Translation**: Docker Desktop transparently handles paths between host and containers
2. **Networking**: Docker Desktop uses a VM with its own network stack
3. **File Permissions**: Different handling of UIDs/GIDs
4. **Volume Mounts**: Docker Desktop has special logic for mounting from inside containers

These differences can cause issues that only appear in production (Linux) but not in local development (macOS).

## Solutions

### 1. Use Real Linux Docker Locally (Recommended)

#### Option A: Colima (Lightweight)
```bash
# Install
brew install colima docker

# Start with production-like settings
colima start --cpu 4 --memory 8 --vm-type=vz --mount-type=virtiofs

# Use it
docker ps  # Now using Linux Docker!

# Stop when done
colima stop
```

#### Option B: Lima (More Control)
```bash
# Install
brew install lima

# Create Docker VM
limactl start --name=docker template://docker

# Set up Docker context
docker context create lima-docker --docker "host=unix://$HOME/.lima/docker/sock/docker.sock"
docker context use lima-docker

# Switch between contexts
docker context use default      # Docker Desktop
docker context use lima-docker  # Real Linux
```

### 2. Force Linux Platform in Development

```yaml
# docker-compose.yml
services:
  crucible-platform:
    platform: linux/amd64  # Force Linux platform even on Mac
    build:
      context: .
      dockerfile: Dockerfile
```

### 3. Test Docker-in-Docker Scenarios

Create a test environment that mimics production:

```dockerfile
# Dockerfile.test-dind
FROM docker:24-dind

# Install Python and dependencies
RUN apk add --no-cache python3 py3-pip

# Copy your app
COPY . /app
WORKDIR /app

# Run with Docker available
CMD ["dockerd-entrypoint.sh", "python3", "-m", "pytest", "tests/docker_integration/"]
```

### 4. Use DevContainers for Consistent Environment

```json
// .devcontainer/devcontainer.json
{
  "name": "Crucible Linux Dev",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:2": {
      "version": "latest",
      "dockerDashComposeVersion": "v2"
    }
  },
  "mounts": [
    // Mount Docker socket for sibling containers
    "source=/var/run/docker.sock,target=/var/run/docker-host.sock,type=bind"
  ],
  "postCreateCommand": "pip install -e .",
  "remoteUser": "vscode"
}
```

### 5. Add Platform Detection

Make your code aware of the environment:

```python
# src/utils/docker_utils.py
import platform
import os

def detect_docker_environment():
    """Detect if we're running on Docker Desktop vs native Linux Docker"""
    
    # Check if we're on macOS
    if platform.system() == 'Darwin':
        return 'docker-desktop-mac'
    
    # Check if we're in WSL
    if 'microsoft' in platform.uname().release.lower():
        return 'docker-desktop-wsl'
    
    # Check for Docker Desktop on Linux
    if os.path.exists('/home/dockerd'):
        return 'docker-desktop-linux'
    
    # Native Linux Docker
    return 'docker-native'

def get_mount_path(container_path: str) -> str:
    """Get the correct mount path based on Docker environment"""
    env = detect_docker_environment()
    
    if env == 'docker-native':
        # Need explicit path translation
        return translate_container_to_host_path(container_path)
    else:
        # Docker Desktop handles this
        return container_path
```

### 6. Automated Testing for Both Environments

```yaml
# .github/workflows/test-docker-environments.yml
name: Test Docker Compatibility

on: [push, pull_request]

jobs:
  test-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Test on Linux Docker
        run: |
          docker-compose up -d
          docker-compose exec -T crucible-platform pytest tests/docker_integration/

  test-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install Colima
        run: |
          brew install colima docker
          colima start
      - name: Test on macOS Docker
        run: |
          docker-compose up -d
          docker-compose exec -T crucible-platform pytest tests/docker_integration/
```

## Quick Reference

### Switching Docker Contexts
```bash
# List available contexts
docker context ls

# Switch to Docker Desktop
docker context use default

# Switch to Linux VM (Colima)
docker context use colima

# Switch to Linux VM (Lima)
docker context use lima-docker
```

### Debugging Path Issues
```bash
# Check what Docker sees
docker run --rm -v $(pwd):/test alpine ls -la /test

# Check from inside container
docker exec crucible-platform ls -la /app/storage/tmp

# Compare mount behavior
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock docker:cli docker info
```

### Common Issues and Fixes

1. **"No such file or directory" in production but works locally**
   - Cause: Docker Desktop's path translation
   - Fix: Use explicit HOST_PWD environment variable

2. **Permission denied on Docker socket**
   - Cause: Different Docker socket permissions
   - Fix: Run as root or use socket proxy

3. **Network connectivity differs**
   - Cause: Docker Desktop's VM networking
   - Fix: Test with `--network=none` locally

## Recommendations

1. **For Daily Development**: Use Colima or Lima
2. **For Quick Tests**: Keep Docker Desktop as fallback
3. **For CI/CD**: Always test on real Linux
4. **For Debugging**: Use platform detection in code

## Further Reading

- [Docker Contexts Documentation](https://docs.docker.com/engine/context/working-with-contexts/)
- [Colima Project](https://github.com/abiosoft/colima)
- [Lima Project](https://github.com/lima-vm/lima)
- [Docker Desktop vs Native Differences](https://docs.docker.com/desktop/faqs/linuxfaqs/#what-is-the-difference-between-docker-desktop-for-linux-and-docker-engine)