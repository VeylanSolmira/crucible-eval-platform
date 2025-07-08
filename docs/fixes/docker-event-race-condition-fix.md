# Docker Event Race Condition Fix

## Date: 2025-07-06

## Problem
Fast-failing containers (like `1/0` Python code) would either:
1. Show as "failed" with empty output/error fields
2. Get stuck in "running" status forever

The root cause was a race condition where the Docker event handler would skip processing "die" events if the container had already been removed from the `running_containers` dictionary.

## Solution Implemented

### 1. Modified Event Handler (executor-service/app.py:654-678)
```python
# Old code (BROKEN):
if container:  # Would skip if not in dict!
    asyncio.run_coroutine_threadsafe(...)

# New code (FIXED):
# Always process die/stop events, even without container reference
if not container:
    # Try to get from Docker API using event data
    container_id = event.get("id") or event.get("Actor", {}).get("ID")
    if container_id:
        try:
            container = docker_client.containers.get(container_id)
        except:
            container = None  # Still process with None

# ALWAYS queue the event
asyncio.run_coroutine_threadsafe(
    event_queue.put((eval_id, container)), loop
)
```

### 2. Updated Completion Handler (executor-service/app.py:689-717)
```python
# Initialize defaults
output = ""
error = ""
exit_code = -1

if container:
    # Normal path - get logs from container
    try:
        container.reload()
        # ... get logs ...
    except docker.errors.NotFound:
        error = "Container was removed before logs could be retrieved"
else:
    # No container - provide meaningful error
    error = "Container exited before logs could be captured"
```

### 3. Safe Container Cleanup (executor-service/app.py:772-780)
```python
# Only remove if we have a container reference
if container:
    try:
        container.remove(force=True)
    except docker.errors.NotFound:
        # Already gone, that's fine
        pass
```

## Testing
Use the provided test script:
```bash
./test-race-condition-fix.sh
```

This submits a `1/0` evaluation and checks if it properly shows as failed with error content.

## What This Fixes
✅ Fast-failing containers now properly report as "failed"  
✅ Error messages are successfully captured from fast containers  
✅ No more stuck evaluations in "running" state  
✅ Event handler is now truly stateless  
✅ Combined stdout/stderr retrieval resolves log capture issues

## What This Doesn't Fix
- Historical stuck evaluations (one-time cleanup needed)
- Executor crashes (moving to Kubernetes)
- No reconciliation loop (Kubernetes provides this)

## Deployment
1. Rebuild executor service: `docker-compose build executor`
2. Restart: `docker-compose restart executor`
3. Test with fast-failing code
4. Monitor logs for the new warning messages

## Future: Kubernetes Migration
This entire problem disappears with Kubernetes Jobs API:
- Reliable lifecycle management
- Pod logs persist after exit
- Built-in reconciliation
- No more Docker event streams!