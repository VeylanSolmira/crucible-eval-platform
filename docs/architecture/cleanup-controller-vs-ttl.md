# Cleanup Controller vs TTL Approach Analysis

Based on my analysis of the code, here are the key benefits of the cleanup controller over a simple TTL approach:

## Current Implementation

- **TTL approach**: Jobs use `ttl_seconds_after_finished=300` (5 minutes) in `dispatcher_service/app.py:757`
- **Cleanup controller**: Active watching and immediate deletion of failed pods

## Benefits of the Cleanup Controller

### 1. Immediate Resource Recovery
- Controller deletes failed pods within seconds (after 10s grace period) - `cleanup_controller.py:97`
- TTL waits full 5 minutes even for crashed pods
- Critical for resource-constrained environments

### 2. Selective Preservation
- Can preserve pods with `debug=true` or `preserve=true` annotations - `cleanup_controller.py:46`
- TTL deletes everything after timeout, no debugging option

### 3. Pod-Level Granularity
- Cleans up individual pods, not just completed jobs
- Handles orphaned pods that jobs might miss

### 4. State-Aware Cleanup
- Only cleans Failed/Succeeded pods - `cleanup_controller.py:51`
- Won't accidentally delete Running/Pending pods
- TTL is time-based only

### 5. Real-time Monitoring
- Uses Kubernetes watch API for instant notification - `cleanup_controller.py:75`
- No polling overhead
- Logs cleanup actions for observability

### 6. Minimal Resource Usage
- Uses only 10m CPU, 32Mi memory - `cleanup-controller.yaml:63`
- More efficient than periodic cleanup jobs

### 7. Resilience
- Auto-restarts watch on failure - `cleanup_controller.py:134`
- Handles API errors gracefully

### 8. Namespace Flexibility
- Can watch single namespace or cluster-wide - `cleanup_controller.py:68`
- TTL is per-job configuration

## Conclusion

The cleanup controller provides better resource utilization, debugging support, and operational visibility compared to simple TTL, especially important for test environments with high pod churn.

## Debug Annotation Implementation

As of the latest update, the platform supports a `debug` flag that can be set when submitting evaluations:

```python
# In tests
eval_id = submit_evaluation(
    code="print('test')", 
    debug=True  # This will add debug=true annotation
)
```

This debug flag propagates through the entire stack:
1. API accepts `debug` parameter in `EvaluationRequest`
2. Celery worker passes it to the dispatcher service
3. Dispatcher adds `debug=true` annotation to the Kubernetes job/pod
4. Cleanup controller skips pods with this annotation

This allows failed pods to be preserved for debugging while still maintaining automatic cleanup for normal operations.

## Hybrid Cleanup Strategy

The platform now implements a hybrid cleanup strategy that combines the benefits of both approaches:

### Normal Pods (debug=false)
- **Immediate cleanup** by cleanup controller for failed pods (within 10 seconds)
- **TTL cleanup** after 10 minutes (600 seconds) for completed jobs
- Optimizes resource usage in production

### Debug Pods (debug=true)
- **Preserved** by cleanup controller (skips pods with debug annotation)
- **TTL cleanup** after 1 hour (3600 seconds) for eventual cleanup
- Provides debugging window while preventing resource leaks

### Configuration
The TTL values are configurable via environment variables:
- `JOB_CLEANUP_TTL`: TTL for normal jobs (default: 300s, configured: 600s)
- `DEBUG_JOB_CLEANUP_TTL`: TTL for debug jobs (default: 3600s)

This hybrid approach ensures:
1. Fast resource recovery for normal operations
2. Adequate debugging time for failed pods
3. Eventual cleanup of all resources
4. No manual intervention required