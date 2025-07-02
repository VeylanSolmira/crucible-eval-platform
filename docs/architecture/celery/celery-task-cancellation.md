# Celery Task Cancellation

## Overview

Task cancellation is a critical feature for production systems where users need the ability to stop long-running or mistakenly submitted evaluations. We implement two distinct cancellation mechanisms:

1. **Task Cancellation** - Prevents queued tasks from running or stops Celery processing
2. **Container Killing** - Forcefully stops already executing Docker containers

## Architecture

### Two Distinct Endpoints

#### `/api/eval/{eval_id}/cancel` - Cancel Celery Task
- Cancels tasks in the Celery queue
- Optionally terminates running Celery workers
- Updates task status to "cancelled"
- Prevents task from consuming resources

#### `/api/eval/{eval_id}/kill` - Kill Docker Container
- Stops running Docker containers
- Used when code is already executing
- Cleans up container resources
- Handles zombie processes

### Implementation Details

#### Celery Task Cancellation
```python
def cancel_celery_task(eval_id: str, terminate: bool = False) -> dict:
    task_id = f"celery-{eval_id}"
    result = AsyncResult(task_id, app=celery_app)
    
    if result.state == 'PENDING':
        # Safe cancellation - task hasn't started
        result.revoke()
    elif result.state in ['STARTED', 'RETRY']:
        if terminate:
            # Force termination of running worker
            result.revoke(terminate=True)
```

#### Task States and Actions

| State | Action | Result |
|-------|--------|--------|
| PENDING | `revoke()` | Task removed from queue |
| STARTED | `revoke(terminate=True)` | Worker process killed |
| SUCCESS | No action | Task already completed |
| FAILURE | No action | Task already failed |
| REVOKED | No action | Already cancelled |

## User Experience

### Frontend Integration
```typescript
// Cancel queued task
await fetch(`/api/eval/${evalId}/cancel`, { method: 'POST' })

// Force terminate running task
await fetch(`/api/eval/${evalId}/cancel?terminate=true`, { method: 'POST' })

// Kill Docker container
await fetch(`/api/eval/${evalId}/kill`, { method: 'POST' })
```

### Decision Flow
1. User clicks "Cancel" button
2. System checks task state:
   - If PENDING → Cancel via Celery
   - If STARTED → Show options:
     - "Cancel" (safe, waits for checkpoint)
     - "Force Stop" (terminate=true)
     - "Kill Container" (Docker kill)

## Safety Considerations

### Graceful Cancellation
- Default behavior is graceful
- Tasks check for cancellation at checkpoints
- Allows cleanup operations
- Preserves partial results

### Forced Termination
- Use sparingly - can leave inconsistent state
- Worker process is killed via SIGTERM
- No cleanup opportunity
- May require manual intervention

### Container Killing
- Last resort for runaway processes
- Sends SIGKILL to container
- Immediate termination
- No graceful shutdown

## Implementation Best Practices

### 1. Predictable Task IDs
```python
task_id = f"celery-{eval_id}"
```
- Allows cancellation without tracking mapping
- Simplifies debugging
- Enables status queries

### 2. State Synchronization
```python
# Update storage after cancellation
await client.put(
    f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}",
    json={"status": "cancelled", "error": "Task cancelled by user"}
)
```

### 3. Cancellation Checks in Tasks
```python
@app.task(bind=True)
def evaluate_code(self, eval_id, code, language):
    # Periodic cancellation checks
    if self.is_aborted():
        logger.info(f"Task {eval_id} was cancelled")
        return {"status": "cancelled"}
```

### 4. Resource Cleanup
```python
try:
    # Task execution
except Exception as e:
    # Cleanup on cancellation
    finally:
        cleanup_resources()
```

## Monitoring and Debugging

### Metrics to Track
- Cancellation rate by type
- Time from request to cancellation
- Failed cancellation attempts
- Orphaned resources

### Common Issues

#### Task Not Found
- Task already completed
- Wrong task ID format
- Task expired from result backend

#### Cancellation Failed
- Worker not responding
- Network partition
- Redis connection issues

#### Zombie Processes
- Container killed but process persists
- Requires manual cleanup
- Consider process monitors

## Security Considerations

### Authorization
- Verify user owns evaluation
- Rate limit cancellation requests
- Audit all cancellation attempts

### Resource Exhaustion
- Limit concurrent cancellations
- Prevent cancellation storms
- Monitor for abuse patterns

## Future Enhancements

### 1. Batch Cancellation
```python
def cancel_multiple_tasks(eval_ids: List[str]):
    # Cancel multiple tasks efficiently
```

### 2. Cancellation Policies
- Auto-cancel after timeout
- Cancel on user logout
- Cancel low-priority on overload

### 3. Partial Results
- Save progress before cancellation
- Allow resume from checkpoint
- Return partial output

## Interview Discussion Points

1. **Why separate cancel vs kill?**
   - Different layers of the stack
   - Different safety guarantees
   - Different use cases

2. **Handling race conditions?**
   - Task starts during cancellation
   - Multiple cancellation requests
   - State synchronization

3. **Scale considerations?**
   - Cancelling thousands of tasks
   - Broadcast vs targeted cancellation
   - Performance impact

4. **Alternative approaches?**
   - Kubernetes Job termination
   - Message queue TTL
   - Circuit breakers