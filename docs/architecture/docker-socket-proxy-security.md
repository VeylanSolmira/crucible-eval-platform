# Docker Socket Proxy Security Architecture

## The Security Regression Problem

In our modularization effort, we moved from:
- **Before**: Creating isolated containers for each code execution
- **After**: Reusing executor containers (less isolation)

This felt like a security regression, which is unacceptable for a platform that evaluates potentially malicious AI code.

## Docker Access Patterns Comparison

### 1. Direct Socket Mount (What We Had)
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```
- **Risk**: Full Docker API access = essentially root on host
- **Attack Surface**: If platform is compromised, attacker can:
  - Execute commands in ANY container
  - Mount ANY host directory
  - Access ALL container secrets
  - Escape to host trivially

### 2. Docker-in-Docker (Common Anti-pattern)
```yaml
services:
  platform:
    privileged: true  # Required for DinD
    # Runs full Docker daemon inside container
```
- **Problems**: Nested containers, storage driver conflicts, requires privileged mode
- **Not Recommended**: Generally considered an anti-pattern

### 3. Docker Socket Proxy (Recommended)
```yaml
services:
  docker-proxy:
    image: tecnativa/docker-socket-proxy
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      CONTAINERS: 1  # Can manage containers
      POST: 1        # Can create containers
      # Explicitly deny dangerous operations
      EXEC: 0        # Cannot exec into containers
      VOLUMES: 0     # Cannot mount volumes
      NETWORKS: 0    # Cannot modify networks
      INFO: 0        # Cannot get system info
```

## How Socket Proxy Works

```
┌─────────────────┐     HTTP/2375     ┌─────────────────┐     Unix Socket     ┌──────────────┐
│  Queue Worker   │ ─────────────────> │  Docker Proxy   │ ─────────────────> │ Docker Daemon │
│ (No socket mount)│                   │ (Filters calls) │                    │   (On host)   │
└─────────────────┘                    └─────────────────┘                    └──────────────┘
```

1. Queue worker makes Docker API calls over TCP (not unix socket)
2. Proxy validates and filters the API calls
3. Only allowed operations are forwarded to real Docker daemon
4. Creates sibling containers (not nested)

## Security Benefits

### Principle of Least Privilege
- Can ONLY create/start/stop containers
- Cannot exec into them (no shell access)
- Cannot mount host volumes (no file access)
- Cannot see other containers' details

### Blast Radius Limitation
If the queue worker is compromised:
- **Without proxy**: Attacker gets root on host
- **With proxy**: Attacker can only create containers (still bad, but contained)

### Audit Trail
- All Docker API calls go through proxy
- Can add logging/monitoring at proxy layer
- Clear separation of concerns

## Implementation Plan

### Phase 1: Add Socket Proxy
1. Add docker-socket-proxy service
2. Configure minimal permissions
3. Keep existing socket mount as fallback

### Phase 2: Update Queue Worker
1. Change from socket mount to TCP connection
2. Update Docker client configuration
3. Test container creation works

### Phase 3: Remove Direct Socket Access
1. Remove socket mount from queue-worker
2. Verify all operations work through proxy
3. Document the security improvement

## Trade-offs

### Complexity
- One more service to manage
- Additional network hop
- Need to understand proxy configuration

### Benefits
- Significant security improvement
- Industry best practice
- Better audit capabilities
- Limits attack surface

## Decision

For a platform evaluating potentially malicious code, the security benefits far outweigh the complexity costs. We should implement the socket proxy pattern.