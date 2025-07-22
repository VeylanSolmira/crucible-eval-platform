# Executor Service

Secure code execution service that creates isolated Docker containers for running untrusted code.

## Overview

The Executor Service is responsible for the actual execution of code submissions. It creates isolated Docker containers with strict security constraints to safely run untrusted code. This service communicates with Docker through a security proxy that enforces additional restrictions.

## Features

- **Container Isolation**: Each execution runs in its own Docker container
- **Resource Limits**: CPU, memory, and disk space restrictions
- **Network Isolation**: Containers run with no network access
- **Security Hardening**: Read-only filesystem, no privileges, security options
- **Timeout Enforcement**: Automatic termination of long-running executions
- **Output Capture**: Collects stdout/stderr from executions
- **Container Cleanup**: Automatic removal of containers after execution
- **OpenAPI Documentation**: Auto-generated API documentation

## API Endpoints

### Execution
- `POST /execute` - Execute code in an isolated container

### Monitoring
- `GET /health` - Health check with Docker connectivity status
- `GET /status` - Service status with recent executions

### Documentation
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)
- `GET /openapi.json` - OpenAPI specification (JSON)
- `GET /openapi.yaml` - OpenAPI specification (YAML)

## Security Features

### Container Restrictions
- **No Network**: `network_mode="none"`
- **Read-Only Root**: Filesystem is read-only except /tmp
- **Resource Limits**: 512MB RAM, 0.5 CPU
- **No New Privileges**: Cannot gain additional privileges
- **Temporary Storage**: 100MB tmpfs for /tmp

### Docker Proxy Integration
The service connects to Docker through a security proxy that:
- Validates container configurations
- Enforces security policies
- Prevents privilege escalation
- Logs all container operations

## Configuration

Environment variables:
- `DOCKER_HOST` - Docker daemon URL (default: `tcp://docker-proxy:2375`)
- `HOSTNAME` - Executor instance ID for tracking
- `PORT` - Service port (default: 8083)

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Queue Worker   │────▶│   Executor   │────▶│Docker Proxy │
└─────────────────┘     └──────────────┘     └─────────────┘
                               │                      │
                               ▼                      ▼
                        ┌──────────────┐       ┌─────────────┐
                        │  Container   │       │Docker Daemon│
                        └──────────────┘       └─────────────┘
```

## Container Lifecycle

1. **Image Check**: Ensures python:3.11-slim is available
2. **Container Creation**: Creates container with security constraints
3. **Code Execution**: Runs the provided code with timeout
4. **Output Collection**: Captures stdout/stderr
5. **Container Cleanup**: Removes container regardless of outcome

## Error Handling

The service handles multiple error scenarios:
- **Image Not Found**: Automatically pulls required image
- **Container Errors**: Captures error output and exit codes
- **Timeouts**: Forcefully stops containers exceeding time limit
- **Docker API Errors**: Reports connectivity issues

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (requires Docker)
python app.py

# Or with uvicorn
uvicorn app:app --reload --port 8083
```

## Docker

```bash
# Build image
docker build -t crucible-executor-service .

# Run container (needs Docker socket access)
docker run -p 8083:8083 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  crucible-executor-service
```

## Integration

The Executor Service integrates with:
- **Queue Worker**: Receives execution requests
- **Docker Proxy**: Validates and forwards Docker commands
- **Storage Service**: Workers store execution results

## Monitoring

Key metrics to monitor:
- Container creation success/failure rates
- Execution timeouts
- Average execution time
- Docker daemon connectivity
- Resource usage (containers created/destroyed)

## Security Considerations

- **Never** expose this service directly to the internet
- Always use through the security proxy in production
- Regularly update the base Python image
- Monitor for unusual container creation patterns
- Implement rate limiting at the API gateway level

## Limitations

- **Single Language**: Currently only supports Python
- **No State**: Containers don't persist state between executions
- **No External Access**: Containers cannot access external resources
- **Limited Resources**: Fixed resource limits for all executions

## Future Improvements

- Support for multiple programming languages
- Dynamic resource allocation based on requirements
- Container image caching for faster startup
- Execution history and metrics collection
- Support for custom container images (with validation)