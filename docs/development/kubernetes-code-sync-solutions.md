# Kubernetes Code Sync Solutions

## Problem Statement
Skaffold file sync is unreliable, and even `kubectl rollout restart` doesn't consistently pick up new code. This document explores solutions for reliably getting code changes into Kubernetes pods without constant no-cache rebuilds.

## Solutions Overview

### 1. Telepresence (External Tool)
**Pros:**
- Intercepts traffic to your pod and routes it to local development
- No rebuilds needed - code runs locally with full cluster access
- Mature tool with strong community support

**Cons:**
- Requires additional tooling outside current stack
- Learning curve for team members
- Potential security concerns with traffic interception

**Usage:**
```bash
brew install datawire/blackbird/telepresence
telepresence intercept <deployment-name> --port 8080:8080
```

### 2. DevSpace (External Tool)
**Pros:**
- More reliable file sync with automatic restart detection
- Supports bidirectional sync and hot reloading
- Better error handling than Skaffold's sync

**Cons:**
- Another tool to learn and maintain
- Migration effort from Skaffold

**Config Example:**
```yaml
dev:
  sync:
  - path: ./api
    containerPath: /app
    onUpload:
      restartContainer: true
```

### 3. Tilt (External Tool)
**Pros:**
- Real-time UI showing build/sync status
- Smart rebuilds only when needed
- Better file watching than Skaffold
- Automatic pod restart on sync

**Cons:**
- Yet another tool in the stack
- Requires Tiltfile configuration

### 4. Fix Current Skaffold Setup (Recommended)
**Pros:**
- Uses existing tooling
- No new dependencies
- Can be environment-specific

**Issues with Current Setup:**
- Multi-stage builds break file sync (files go to wrong stage)
- Missing proper cache invalidation
- No automatic container restart on sync

**Proposed Fixes:**

#### a. Add Cache Busting for Dev Environment
```yaml
profiles:
- name: dev
  build:
    artifacts:
    - image: crucible-platform/api-service
      context: .
      docker:
        dockerfile: api/Dockerfile
        buildArgs:
          CACHEBUST: "{{.TIMESTAMP}}"
        cacheFrom: []  # Disable cache in dev
    tagPolicy:
      inputDigest: {}  # Force new digest on every change
```

#### b. Fix Multi-Stage Build Issues
Ensure COPY commands in runtime stage properly reference builder stage:
```dockerfile
# Runtime stage
FROM ${BASE_IMAGE} AS runtime
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
```

#### c. Add Container Restart on Sync
```yaml
sync:
  manual:
  - src: "api/**/*.py"
    dest: /app
    strip: "api/"
  hooks:
    after:
    - container:
        command: ["sh", "-c", "kill 1"]  # Force container restart
```

### 5. Quick Fix: Volume Mounts (Development Only)
**Pros:**
- Immediate file updates
- No sync needed
- Simple to implement

**Cons:**
- Only works with local Kubernetes (Docker Desktop, Minikube)
- Security concerns in production
- Performance issues with large codebases

**Implementation:**
```yaml
volumes:
- name: code
  hostPath:
    path: /path/to/local/code
    type: Directory
volumeMounts:
- name: code
  mountPath: /app
  readOnly: false
```

## Recommended Approach

For immediate relief using current tools:

1. **Implement Skaffold cache busting in dev profile**
2. **Fix multi-stage Docker builds to properly support sync**
3. **Add container restart hooks after sync**
4. **Consider volume mounts for local development only**

## Investigation Tasks

1. Test cache busting with `CACHEBUST` build arg
2. Verify sync works with fixed multi-stage builds
3. Benchmark rebuild times with cache disabled
4. Document any remaining sync reliability issues
5. Create runbook for developers when sync fails

## Fallback Procedures

When sync fails:
1. Try `kubectl rollout restart deployment/<name>`
2. Delete the pod: `kubectl delete pod <pod-name>`
3. Use `skaffold build --cache-artifacts=false` for forced rebuild
4. As last resort: `skaffold delete && skaffold run`

## Understanding Uvicorn Reload Issues

The `pkill -HUP uvicorn` hook is trying to send a SIGHUP (hangup) signal to the Uvicorn process to trigger a graceful reload. Here's what's happening:

### What Uvicorn reload means:
- Uvicorn is a Python ASGI server (commonly used with FastAPI/Starlette)
- When it receives SIGHUP, it's supposed to reload the Python application
- This would re-import your Python modules, picking up code changes

### But here's the catch: Uvicorn doesn't support SIGHUP reloading by default!

Uvicorn only reloads in two scenarios:
1. When run with `--reload` flag (watches files automatically)
2. When using `--workers` with Gunicorn as the process manager

### What's likely happening in your containers:

If running Uvicorn directly:
```dockerfile
# This won't reload on SIGHUP
CMD ["uvicorn", "app:app", "--host", "0.0.0.0"]

# This will auto-reload on file changes (dev only)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--reload"]
```

If using Gunicorn + Uvicorn:
```dockerfile
# This WILL reload on SIGHUP
CMD ["gunicorn", "app:app", "-k", "uvicorn.workers.UvicornWorker", "--reload"]
```

### Why your sync might be working anyway:
1. If Uvicorn is running with `--reload`, it's already watching for file changes
2. If your app creates new instances on each request, it naturally picks up changes
3. If you're using FastAPI's dependency injection, new code loads on new requests

### To check what's actually running:
```bash
kubectl exec -it <pod> -- ps aux | grep -E "(uvicorn|gunicorn|python)"
```

### The better approach for your setup:

**Option 1** - Use Uvicorn's built-in reload:
```dockerfile
# In your Dockerfile for dev
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--reload", "--reload-dirs", "/app"]
```

**Option 2** - Remove the hook and rely on file watching:
```yaml
sync:
  manual:
    - src: "api/**/*.py"
      dest: /app
      strip: "api/"
  # No hooks - let uvicorn --reload handle it
```

**Option 3** - Use Gunicorn if you need SIGHUP:
```dockerfile
CMD ["gunicorn", "app:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--reload"]
```

### Analysis

The irony is that the `pkill -HUP uvicorn` command is trying to implement something that Uvicorn either:
- Already does better with `--reload`
- Doesn't support without Gunicorn

That's why removing the hooks entirely is probably the best solution - you're trying to manually trigger something that should be automatic in a dev environment.

### Python equivalent of pkill

For reference, `pkill -HUP -f uvicorn` is NOT equivalent to `os.kill(1, signal.SIGHUP)`:
- `pkill -HUP -f uvicorn` - Finds processes matching "uvicorn" and sends SIGHUP to them
- `os.kill(1, signal.SIGHUP)` - Sends SIGHUP to PID 1 only

The Python equivalent would require `pgrep` which also isn't installed in minimal containers.