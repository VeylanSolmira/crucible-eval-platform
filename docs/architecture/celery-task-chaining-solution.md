# Celery Task Chaining Solution for Executor Management

## Overview

This document describes the task chaining solution to handle executor availability without running into Celery + Redis retry limitations.

## The Core Problem

- We have limited executors (currently 3)
- Tasks need to wait for available executors
- Celery + Redis can't handle infinite retries (throws "Can't retry" errors)
- Original single-task design mixed resource discovery with execution

## The Solution: Task Chaining

Split the evaluation process into two separate Celery tasks:

1. **Assigner Task**: Lightweight task that only finds available executors (can retry freely)
2. **Worker Task**: Performs actual code execution (has an executor, limited retries)

### Implementation

```python
@app.task(bind=True, max_retries=None, result_expires=60)
def assign_executor(self, eval_id: str, code: str, language: str):
    """
    Task 1: Just finds an available executor
    This task CAN retry because it does minimal work
    """
    executor_url = get_available_executor_url()
    
    if not executor_url:
        # No executor? Retry in 5 seconds
        # This retry works fine because this task does almost nothing
        logger.info(f"No executor for {eval_id}, retrying...")
        raise self.retry(countdown=5)
    
    # Store assigner task ID for potential cancellation
    redis_client.setex(f"assigner:{eval_id}", 300, self.request.id)
    
    # Found executor! Now chain to the actual work
    # .si() means "signature immutable" - passes specific args
    evaluation_task = evaluate_code.si(
        eval_id=eval_id,
        code=code,
        language=language,
        executor_url=executor_url  # Pass the found executor
    )
    
    # Clean up assigner tracking
    redis_client.delete(f"assigner:{eval_id}")
    
    # Start the evaluation task
    return evaluation_task.apply_async()

@app.task(
    autoretry_for=(httpx.HTTPError, httpx.ConnectTimeout),
    retry_kwargs={"max_retries": 3},
    retry_backoff=True
)
def evaluate_code(eval_id: str, code: str, language: str, executor_url: str):
    """
    Task 2: Actually runs the code
    This task already HAS an executor, so no waiting/polling needed
    """
    logger.info(f"Evaluating {eval_id} on {executor_url}")
    
    # Update status
    update_evaluation_status(eval_id, "running", {"executor": executor_url})
    
    # Execute the code
    response = httpx.post(
        f"{executor_url}/execute",
        json={"eval_id": eval_id, "code": code, "language": language},
        timeout=300
    )
    
    result = response.json()
    update_evaluation_status(eval_id, "completed", result)
    
    return result
```

### Flow Diagram

```
Client Request
    |
    v
[assign_executor task]
    |
    ├─ No executor? ──> retry in 5s ──> [assign_executor task] (again)
    |
    └─ Found executor? ──> [evaluate_code task] ──> HTTP call ──> Result
```

## Handling Multiple Workers with Atomic Executor Allocation

With multiple Celery workers, we need atomic executor allocation to prevent double-booking.

### Solution: Redis Atomic Pop (Recommended)

```python
def get_available_executor_url() -> Optional[str]:
    """Atomically claim an executor from the pool"""
    # RPOP is atomic - only one worker gets the executor
    executor_data = redis_client.rpop("available_executors")
    
    if executor_data:
        executor_info = json.loads(executor_data)
        executor_url = executor_info["url"]
        
        # Mark as in-use with TTL (in case of failures)
        redis_client.setex(
            f"executor:busy:{executor_url}",
            300,  # 5 minute TTL
            eval_id
        )
        
        return executor_url
    return None

def release_executor(executor_url: str):
    """Return executor to available pool"""
    redis_client.delete(f"executor:busy:{executor_url}")
    redis_client.lpush("available_executors", json.dumps({
        "url": executor_url,
        "last_used": time.time()
    }))

@app.task(bind=True, max_retries=30)
def assign_executor(self, eval_id: str, code: str, language: str):
    # This is atomic - no double-allocation possible
    executor_url = get_available_executor_url()
    
    if not executor_url:
        raise self.retry(countdown=5)
    
    # Chain to evaluation with cleanup
    task = evaluate_code.si(eval_id, code, language, executor_url)
    
    # Important: Link cleanup task for failures
    cleanup = release_executor_task.si(executor_url)
    task.link_error(cleanup)  # Run cleanup if evaluation fails
    task.link(cleanup)        # Run cleanup on success too
    
    return task.apply_async()

@app.task
def release_executor_task(executor_url: str):
    """Cleanup task that always runs after evaluation"""
    release_executor(executor_url)
```

### Why This Works

1. **Redis LIST operations are atomic**: RPOP ensures only one worker gets each executor
2. **Built-in ordering**: FIFO/LIFO for fair executor distribution
3. **TTL on busy markers**: Prevents deadlock if a worker crashes
4. **Natural load balancing**: Executors are distributed evenly

### Alternative Solutions

#### Solution 2: Redis Lua Script (Most Robust)

```python
# Lua script for atomic executor allocation
CLAIM_EXECUTOR_SCRIPT = """
local available_key = KEYS[1]
local busy_prefix = KEYS[2]
local eval_id = ARGV[1]
local ttl = ARGV[2]

-- Get all available executors
local executors = redis.call('SMEMBERS', available_key)

for i, executor in ipairs(executors) do
    local busy_key = busy_prefix .. executor
    -- Try to claim this executor
    if redis.call('SET', busy_key, eval_id, 'NX', 'EX', ttl) then
        -- Success! Remove from available set
        redis.call('SREM', available_key, executor)
        return executor
    end
end

return nil
"""
```

#### Solution 3: Distributed Lock Pattern

Use redis_lock for exclusive access during allocation.

#### Solution 4: Executor Health Check + Atomic Claim

Verify executor health before allocation.

## Benefits of Task Chaining

1. **Clean Separation**: Waiting logic isolated from execution logic
2. **Both Tasks Can Retry**: But for different reasons
3. **Monitoring**: Can track how long evaluations wait vs execute
4. **Scalable**: Can have different worker pools for each task type
5. **No Redis Retry Issues**: Lightweight assigner task doesn't hit retry limitations

## Implementation Notes

- Track assigner task IDs for cancellation support
- Use task linking for proper cleanup
- Consider separate worker pools for assigners vs evaluators
- Monitor queue depths separately

## Multiple Celery Workers

Currently we run a single Celery worker with concurrency matching executor count. If expanding to multiple workers:

### The Problem
- Multiple workers might try to claim the same executor simultaneously
- Need atomic allocation to prevent double-booking
- Must handle worker failures gracefully

### The Solution
The Redis atomic pop pattern (Solution 1) handles this automatically:
- Each worker tries to RPOP from the executor pool
- Redis guarantees only one worker gets each executor
- Failed workers release executors back to the pool via TTL

### Configuration for Multiple Workers
```python
# Worker 1
celery -A tasks worker --concurrency=3 --hostname=worker1@%h

# Worker 2  
celery -A tasks worker --concurrency=3 --hostname=worker2@%h

# Now 6 concurrent tasks can try to claim from 3 executors
# The atomic pop ensures clean allocation
```

## Future Considerations

When moving to Kubernetes, this pattern can be simplified as K8s provides native:
- Service discovery
- Health checks
- Load balancing
- Resource limits

But until then, this task chaining solution provides a robust way to handle executor allocation within Celery's constraints.