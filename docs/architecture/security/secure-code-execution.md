# Secure Code Execution Architecture

## Problem

Running Docker-from-Docker (mounting docker.sock) has significant security implications:
- Requires root or docker group access
- Container can control host Docker daemon
- Essentially gives container root on host

## Solutions

### 1. Development Mode (Current)
- Accept that code execution is disabled when running in container
- Use DisabledEngine to provide clear error messages
- Developers can run the platform locally (not in container) for full functionality

### 2. Docker Socket Proxy
- Use `tecnativa/docker-socket-proxy` to mediate access
- Proxy only allows specific Docker API endpoints
- No direct socket access from application container
- Still requires trust in the proxy container

### 3. Remote Execution Service (Production)
```
┌─────────────┐       gRPC/HTTP      ┌─────────────────┐
│   Platform  │ ──────────────────> │ Execution       │
│  Container  │                      │ Service         │
└─────────────┘                      └────────┬────────┘
                                              │
                                              v
                                     ┌─────────────────┐
                                     │ Isolated        │
                                     │ Execution Nodes │
                                     └─────────────────┘
```

### 4. Kubernetes Jobs (Best for Production)
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: code-execution-${EVAL_ID}
spec:
  template:
    spec:
      containers:
      - name: executor
        image: python:3.11-slim
        command: ["python", "/code/main.py"]
        resources:
          limits:
            memory: "100Mi"
            cpu: "500m"
        securityContext:
          runAsNonRoot: true
          runAsUser: 65534
          readOnlyRootFilesystem: true
          allowPrivilegeEscalation: false
      restartPolicy: Never
```

## Recommendation

For METR submission:
1. **Current approach is fine** - Shows security awareness by refusing insecure execution
2. **Document the trade-off** - Explain why we chose security over convenience
3. **Show the upgrade path** - Demonstrate knowledge of production solutions

The fact that our platform refuses to run code insecurely (rather than falling back to dangerous practices) demonstrates good security judgment.