# Docker Logs Issue with Fast-Failing Containers - RESOLVED

## Date: 2025-07-06

## Issue
Fast-failing containers (like `1/0` Python code) were showing as "failed" but with empty output/error fields, even though the container produced output when run directly.

## Current Status
✅ FIXED - Both the Docker event race condition and log retrieval have been resolved:
- ✅ Events are now always processed (even if container not in running_containers dict)
- ✅ Completion handler works with or without container reference
- ✅ Logs are successfully retrieved for fast-failing containers

## Investigation Summary

### What We Fixed
1. **Event Handler Race Condition**
   - Previously: Events dropped if container not in `running_containers` dict
   - Now: Always process die/stop events, try to retrieve container from Docker API

2. **Graceful Handling of Missing Containers**
   - Added proper error messages when container is gone
   - Completion handler no longer crashes on None container

### What's Still Broken
Despite the fixes, logs are empty for fast-failing containers. The timeline shows:
- Container starts
- Container exits within ~500ms
- Event handler DOES receive the die event
- Completion handler DOES process it
- But `container.logs()` returns empty strings

### Theories
1. **Log Driver Buffering**: Docker's json-file log driver might not flush logs immediately
2. **API Timing**: The Docker API might need a moment after container exit to make logs available
3. **TTY vs Non-TTY**: We use `tty=True` which might affect log flushing behavior

### The Solution
The key was retrieving stdout and stderr together in a single call:
```python
# Before (separate calls - didn't work)
output = container.logs(stdout=True, stderr=False).decode("utf-8")
error = container.logs(stdout=False, stderr=True).decode("utf-8")

# After (single call - works!)
logs = container.logs(stdout=True, stderr=True).decode("utf-8")
if exit_code == 0:
    output = logs
    error = ""
else:
    output = ""
    error = logs
```

Making separate calls for stdout/stderr was somehow missing the output for very fast containers. Combining them into a single call resolved the issue.

### Current Limitation
The current solution mixes stdout and stderr together. For example:
```python
print("Starting...")      # stdout
print("Processing...")     # stdout
1/0                       # stderr (traceback)
```

Would all appear together in the `error` field when exit code != 0. To properly separate them, we'd need to use Docker's streaming API with multiplexed output parsing, which adds complexity. For now, this is acceptable for the demo.

### Why Separating stdout/stderr is Hard with Docker

The Docker API has two modes for log retrieval that don't work well with dead containers:

**Mode 1: Simple logs (current approach)**
```python
logs = container.logs(stdout=True, stderr=True)
# Returns everything mixed together as bytes/string
```

**Mode 2: Stream with demux**
```python
logs = container.logs(stdout=True, stderr=True, stream=True, demux=True)
# Returns (stdout_generator, stderr_generator)
# Often fails on dead containers!
```

When a container dies quickly, the streaming approach often fails because the generators are already closed. The workaround involves manually parsing Docker's multiplexed log format, which uses a binary protocol:
- `[STREAM_TYPE(1)][PADDING(3)][SIZE(4)][DATA(SIZE)]`

This is complex and error-prone for what should be a simple operation.

### How Kubernetes Solves This

This problem largely disappears in Kubernetes because:

1. **Persistent Logs After Pod Death**
   ```bash
   kubectl logs <pod-name> --previous
   # Logs retained for 24-48 hours after pod completion
   ```

2. **Native stdout/stderr Separation**
   - Container runtimes (containerd/CRI-O) handle streams properly
   - Each log line includes stream metadata
   ```json
   {
     "timestamp": "2024-01-01T12:00:00Z",
     "stream": "stderr",
     "log": "Traceback (most recent call last):\n"
   }
   ```

3. **Better APIs**
   ```python
   # Kubernetes Python client
   v1 = client.CoreV1Api()
   logs = v1.read_namespaced_pod_log(
       name=pod_name,
       namespace='default',
       previous=True,  # Get logs from previous (dead) container
       timestamps=True
   )
   ```

4. **Centralized Logging**
   - Production Kubernetes uses log aggregation (ELK, Loki, Fluentd)
   - Captures everything regardless of container state
   - Streams are properly tagged and searchable

## Conclusion

For the current Docker-based implementation, we're accepting that stdout/stderr are mixed together. This is a reasonable compromise for the demo since:
- The main issue (no logs at all for fast containers) is fixed
- Proper separation would require complex multiplexed format parsing
- Kubernetes will provide proper separation when we migrate

## Next Steps for Investigation

1. **Test with different log drivers**
   ```python
   # Try with journald or local log driver
   log_config=docker.types.LogConfig(type="local")
   ```

2. **Force flush before exit**
   ```python
   # Wrap user code to ensure flush
   code_wrapper = f"""
   import sys
   try:
       {user_code}
   finally:
       sys.stdout.flush()
       sys.stderr.flush()
   """
   ```

3. **Use container.attach() instead of logs()**
   ```python
   # Attach to container output streams before it starts
   stdout = container.attach(stdout=True, stream=True)
   ```

4. **Check Docker daemon logs**
   - Look for any warnings about log retrieval
   - Check if this is a known Docker issue

## Workaround for Demo
For the demo, we could:
1. Add a wrapper script that ensures output is captured
2. Use a different execution approach for very short scripts
3. Document this as a known limitation

## Related Files
- `/executor-service/app.py` - Contains TODO comment at line 706
- `/docs/debugging/missing-logs-race-condition.md` - Full debugging journey
- `/docs/fixes/docker-event-race-condition-fix.md` - What we fixed so far