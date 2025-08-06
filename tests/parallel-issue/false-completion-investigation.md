# False Job Completion Investigation

## The Real Problem
The coordinator is detecting jobs as complete (no active pods) while tests are still running:
- Integration tests: Only 17/25 tests shown as PASSED before output stops
- Job marked as failed at 153.5s, but should have run for ~165s based on individual run

## Possible Causes

### 1. Pod Crash/OOMKill
The test runner pod might be getting killed due to:
- Memory limits exceeded (currently 512Mi)
- CPU throttling
- Node eviction due to resource pressure

### 2. Kubernetes API Lag
The job status might show `active: 0` temporarily due to:
- API server lag under high load
- Pod transitioning between states
- Network issues between coordinator and API server

### 3. Pod Completion vs Job Completion
The pod might be marked as completed/failed while:
- Container is still writing output
- Exit handlers are still running
- Logs are still being flushed

### 4. Parallel Execution Side Effects
Running two test suites might cause:
- Shared resource contention (Redis, PostgreSQL)
- API rate limiting
- Network policy issues

## Investigation Steps

1. Check pod status during parallel runs:
   ```bash
   kubectl get pods -n dev -l test-run=<timestamp> -w
   ```

2. Check pod termination reasons:
   ```bash
   kubectl describe pod <test-pod-name> -n dev
   ```

3. Add more detailed status logging in coordinator.py:
   ```python
   print(f"Job status: {json.dumps(status, indent=2)}")
   ```

4. Check if pods are being evicted:
   ```bash
   kubectl get events -n dev --field-selector reason=Evicted
   ```