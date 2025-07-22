# Cancellation Race Condition Analysis

## Problem Statement

There's a race condition window during evaluation cancellation where a Kubernetes job can be created after we've marked an evaluation as cancelled, resulting in orphaned jobs.

## Race Condition Scenario

1. **T0**: Celery worker picks up evaluation task
2. **T1**: Worker updates status to "provisioning"
3. **T2**: Worker makes HTTP call to dispatcher to create K8s job
4. **T3**: User requests cancellation
5. **T4**: Cancel handler checks status (provisioning), tries kill
6. **T5**: Kill returns 404 (no K8s job exists yet)
7. **T6**: Cancel handler updates status to "cancelled"
8. **T7**: Dispatcher finally receives/processes the request from T2
9. **T8**: Dispatcher creates K8s job
10. **Result**: Orphaned K8s job running for a cancelled evaluation

## Why Current Mitigations Are Insufficient

### Option 1: Dispatcher Status Check
```python
# In dispatcher's execute endpoint
eval_status = check_evaluation_status(eval_id)
if eval_status in ["cancelled", "failed", "completed"]:
    return {"error": "Evaluation already in terminal state"}
```

**Problem**: Still has a race condition between status check and job creation.

### Option 2: Creation Lock
Using Redis lock during job creation.

**Problem**: Complex to implement correctly, needs timeout handling, distributed lock edge cases.

## Potential Long-term Solutions

### Option 3: Request Token Pattern
- Celery worker generates unique token when calling dispatcher
- Token stored in Redis with TTL
- Cancel operation invalidates token
- Dispatcher validates token before creating job

### Option 4: State Machine with Atomic Operations
- Use Redis atomic operations (SET NX) to claim "creating" state
- Cancel operation can set "cancel_requested" flag
- Dispatcher checks flag before and after job creation

### Option 5: Two-Phase Commit
- Phase 1: Dispatcher reserves resources, returns reservation ID
- Phase 2: Celery worker confirms reservation
- Cancel can interrupt between phases

### Option 6: Event Sourcing
- All state changes go through event stream
- Dispatcher subscribes to cancellation events
- Can abort job creation if cancellation event received

## Interim Solution: Orphan Job Cleanup

### Implementation

1. **Periodic Cleanup Job** (runs every 5 minutes)
   - **Status**: Draft manifest created but not yet integrated into Kustomization
   - **Location**: `/k8s/base/cleanup/orphan-job-cleanup-cronjob.yaml`
   - **Note**: This manifest exists in the codebase but is not deployed as it's not referenced in any kustomization.yaml
   ```python
   async def cleanup_orphaned_jobs():
       # Get all K8s jobs with eval-id label
       jobs = get_all_evaluation_jobs()
       
       for job in jobs:
           eval_id = job.metadata.labels.get("eval-id")
           if not eval_id:
               continue
               
           # Check evaluation status
           eval_status = get_evaluation_status(eval_id)
           
           # If evaluation is in terminal state but job exists
           if eval_status in ["cancelled", "failed", "completed"]:
               # Job shouldn't exist
               logger.warning(f"Found orphaned job {job.metadata.name} for {eval_status} evaluation {eval_id}")
               delete_job(job.metadata.name)
   ```

2. **Storage Worker Enhancement**
   - Listen for job creation events
   - Check if evaluation is already cancelled
   - Log warning and trigger cleanup

3. **Metrics**
   - Track orphaned jobs found/cleaned
   - Alert if rate exceeds threshold

### Benefits of Interim Approach
- Simple to implement
- No changes to critical path
- Provides visibility into problem frequency
- Can be removed once permanent solution implemented

### Drawbacks
- Not real-time (up to 5 minute delay)
- Wastes some resources running orphaned jobs
- Requires monitoring to ensure cleanup is working

## Migration Path

1. **Phase 1**: Implement cleanup job (current)
2. **Phase 2**: Add metrics and monitoring
3. **Phase 3**: Implement token-based solution
4. **Phase 4**: Remove cleanup job

## Related Issues

- Similar race condition might exist with kill operation during job startup
- Need to ensure cleanup doesn't interfere with legitimate jobs
- Consider impact on job metrics/billing