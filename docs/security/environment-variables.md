# Environment Variables and Security Considerations

## Overview

The Crucible platform uses environment variables for configuration to maintain flexibility across different deployment environments while avoiding information leakage about the runtime environment.

## Security Principles

1. **No Container Detection**: Environment variables should not reveal whether the application is running in a container, VM, or bare metal
2. **Principle of Least Privilege**: Default to most restrictive settings (localhost) unless explicitly configured
3. **Generic Names**: Use deployment-agnostic variable names

## Environment Variables

### `BIND_HOST`
- **Purpose**: Controls which network interfaces the server binds to
- **Default**: `localhost` (most secure - local access only)
- **Docker Value**: `0.0.0.0` (required for container port mapping)
- **Security Note**: Only set to `0.0.0.0` when necessary for container deployment

### `SERVICE_HOST`
- **Purpose**: Hostname for inter-service communication
- **Default**: `localhost` (for monolithic/local development)
- **Docker Value**: `crucible` (Docker Compose service name)
- **Security Note**: Generic name that doesn't reveal containerization

### `PLATFORM_HOST`
- **Purpose**: API gateway hostname for frontend-to-backend communication
- **Default**: `localhost`
- **Docker Value**: `crucible` (when services are co-located)
- **Security Note**: Used for future microservices architecture

## Local Development vs Production

### Local Development (Default)
```bash
# No environment variables needed - secure defaults
python app.py
# Server binds to localhost:8080 - only accessible locally
```

### Docker Development
```yaml
# docker-compose.yml
environment:
  - BIND_HOST=0.0.0.0      # Required for port mapping
  - SERVICE_HOST=crucible  # For inter-container communication
```

### Production Deployment
```bash
# Set only what's needed
export BIND_HOST=10.0.0.5  # Bind to specific internal IP
export SERVICE_HOST=api-gateway.internal  # Internal DNS name
```

## Security Best Practices

1. **Never hardcode `0.0.0.0`** in application code
   - Always use environment variables
   - Default to `localhost` for security

2. **Don't reveal runtime environment**
   - Avoid variables like `IN_DOCKER`, `IS_CONTAINER`, `CONTAINER_ENV`
   - Use generic names that apply to any deployment

3. **Validate environment variables**
   ```python
   # Good: Validate and restrict values
   bind_host = os.environ.get('BIND_HOST', 'localhost')
   if bind_host not in ['localhost', '127.0.0.1', '0.0.0.0']:
       # Could also validate against specific IPs
       raise ValueError(f"Invalid BIND_HOST: {bind_host}")
   ```

4. **Log configuration (not secrets)**
   ```python
   # Good: Log what interface we're binding to
   print(f"Starting server on {bind_host}:{port}")
   
   # Bad: Don't log that reveals environment
   print(f"Running in Docker: {in_docker}")
   ```

## Information Leakage Risks

### What NOT to Do

```python
# BAD: Reveals containerization
if os.path.exists('/.dockerenv'):
    host = '0.0.0.0'
    
# BAD: Environment-specific variable names
if os.environ.get('KUBERNETES_SERVICE_HOST'):
    print("Running in Kubernetes")
    
# BAD: Container-specific error messages
except Exception as e:
    if 'docker' in str(e).lower():
        return "Container networking error"
```

### What to Do Instead

```python
# GOOD: Generic configuration
host = os.environ.get('BIND_HOST', 'localhost')

# GOOD: Generic error messages
except Exception as e:
    return "Network configuration error"

# GOOD: Environment-agnostic logging
logger.info(f"Service starting on {host}:{port}")
```

## Testing Configuration

### Test Script
```python
#!/usr/bin/env python3
import os

# Show current configuration without revealing environment
print("Current Configuration:")
print(f"  Bind Host: {os.environ.get('BIND_HOST', 'localhost')}")
print(f"  Service Host: {os.environ.get('SERVICE_HOST', 'localhost')}")
print(f"  Platform Host: {os.environ.get('PLATFORM_HOST', 'localhost')}")

# Don't print things like:
# - "Running in Docker: True"
# - "Container ID: abc123"
# - "Kubernetes Pod: my-pod"
```

## Summary

By using generic environment variables and defaulting to secure settings, we achieve:
- **Flexibility**: Same code runs locally, in Docker, or in production
- **Security**: No information leakage about runtime environment
- **Simplicity**: Clear, consistent configuration model