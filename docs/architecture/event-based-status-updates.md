# Event-Based Status Updates for Kubernetes Jobs

## Current State

After migrating from Docker to Kubernetes, we lost event-based status updates. Currently:
- Celery worker polls the dispatcher API for job status
- Updates are delayed and create unnecessary load
- The 403 error was fixed by adding `jobs/status` permission

## Alternatives for Event-Based Updates

### 1. Sidecar Container Approach
```yaml
apiVersion: batch/v1
kind: Job
spec:
  template:
    spec:
      containers:
      - name: evaluation
        image: executor-ml
        command: ["python", "-u", "-c", "user_code_here"]
      - name: event-publisher
        image: status-reporter:latest
        env:
        - name: EVAL_ID
          value: "eval_123"
        - name: REDIS_URL
          value: "redis://redis:6379"
```

**Pros:**
- Clean separation of concerns
- No modification to executor images
- Can monitor main container via K8s API

**Cons:**
- More complex Job specification
- Coordination between containers
- Sidecar doesn't know when main container is "done"

### 2. Init Container + Wrapper Script
```yaml
spec:
  initContainers:
  - name: setup
    image: platform-tools
    command: ["cp", "/scripts/wrapper.sh", "/shared/"]
  containers:
  - name: evaluation
    command: ["/shared/wrapper.sh", "python", "-c", "user_code"]
```

**Pros:**
- Single container execution model
- Can intercept exit codes and output
- Flexible wrapper logic

**Cons:**
- Requires shared volume
- Modifies execution environment
- Additional complexity in Job spec

### 3. Built-in Event Publishing (Wrapper in Image)
```dockerfile
# In executor-ml/Dockerfile
COPY event_wrapper.py /
ENTRYPOINT ["python", "/event_wrapper.py"]
```

```python
#!/usr/bin/env python3
import subprocess
import sys
import os
import redis
import json
import time

def main():
    eval_id = os.environ.get('EVAL_ID')
    user_code = os.environ.get('USER_CODE')
    redis_url = os.environ.get('REDIS_URL', 'redis://redis:6379')
    
    # Connect to Redis
    r = redis.from_url(redis_url)
    
    # Publish running event
    r.publish('evaluation:running', json.dumps({
        'eval_id': eval_id,
        'timestamp': time.time()
    }))
    
    # Run the actual code
    start_time = time.time()
    result = subprocess.run(
        [sys.executable, '-c', user_code],
        capture_output=True,
        text=True
    )
    duration = time.time() - start_time
    
    # Publish completion event
    event = {
        'eval_id': eval_id,
        'exit_code': result.returncode,
        'output': result.stdout,
        'error': result.stderr,
        'duration_seconds': duration,
        'timestamp': time.time()
    }
    
    if result.returncode == 0:
        r.publish('evaluation:completed', json.dumps(event))
    else:
        r.publish('evaluation:failed', json.dumps(event))
    
    # Exit with same code
    sys.exit(result.returncode)

if __name__ == '__main__':
    main()
```

**Pros:**
- Simplest Job specification
- Most reliable - always captures output
- No coordination issues
- Proven pattern (used by CI/CD systems)

**Cons:**
- Couples executor image to platform
- Requires Redis access from evaluation pods

### 4. Kubernetes Lifecycle Hooks
```yaml
lifecycle:
  postStart:
    exec:
      command: ["/scripts/notify-start.sh"]
  preStop:
    exec:
      command: ["/scripts/notify-stop.sh"]
```

**Pros:**
- Native Kubernetes feature
- No wrapper needed

**Cons:**
- preStop doesn't run on successful completion
- No access to container output
- Limited usefulness for our case

### 5. Job Controller (Kubernetes Operator)
Create a separate service that watches Job events:

```python
from kubernetes import client, config, watch

def job_controller():
    v1 = client.BatchV1Api()
    w = watch.Watch()
    
    for event in w.stream(v1.list_namespaced_job, namespace='crucible'):
        job = event['object']
        event_type = event['type']
        
        if job.metadata.labels.get('app') == 'evaluation':
            eval_id = job.metadata.labels.get('eval-id')
            
            if event_type == 'MODIFIED':
                if job.status.active:
                    publish_event('evaluation:running', {'eval_id': eval_id})
                elif job.status.succeeded:
                    # Fetch logs and publish completion
                    logs = get_job_logs(job.metadata.name)
                    publish_event('evaluation:completed', {
                        'eval_id': eval_id,
                        'output': logs
                    })
```

**Pros:**
- Complete decoupling
- Works with any Job/executor
- Can add sophisticated logic

**Cons:**
- Another service to deploy and maintain
- Still needs to fetch logs separately
- Might miss rapid state changes

## Recommendation: Built-in Wrapper (Option 3)

The built-in wrapper approach is recommended because:

1. **Simplicity** - Just works out of the box
2. **Reliability** - Guaranteed to capture all output and exit codes
3. **Performance** - No polling or coordination overhead
4. **Proven Pattern** - Standard approach in CI/CD systems
5. **Minimal Coupling** - Wrapper is generic, only publishes events

The concern about coupling is minimal because:
- The wrapper doesn't know about platform internals
- It only needs Redis URL and eval ID
- Could be made pluggable (e.g., support different event backends)

## Implementation Steps

1. Create `event_wrapper.py` with Redis event publishing
2. Update executor Dockerfiles to include wrapper
3. Update dispatcher to pass `USER_CODE` as environment variable
4. Remove polling logic from Celery worker
5. Test event flow end-to-end

## Alternative: Hybrid Approach

Keep polling as fallback but add event-based updates:
- Wrapper publishes events when possible
- Celery still polls but at lower frequency
- Best of both worlds - events for speed, polling for reliability

## Benefits of Event-Driven Architecture

- **Reduced Latency**: Near-instant status updates vs 10-second polling intervals
- **Lower Resource Usage**: No constant polling of Kubernetes API
- **Better User Experience**: Real-time feedback on evaluation progress
- **Scalability**: Event streams handle high load better than polling
- **Future-Proof**: Enables features like live output streaming, progress bars, etc.