# Executor Capacity Management in Distributed Systems

## Problem Statement

When running multiple Celery workers that need to allocate tasks to a limited pool of executors, we face a classic distributed systems race condition:

1. **Multiple Workers**: 3 Celery workers running concurrently
2. **Limited Resources**: 3 executors, each can handle 1 task
3. **Race Condition**: All workers might check capacity simultaneously and try to claim the same executor

## Current Implementation

We've implemented a Kubernetes-like readiness probe pattern:

### 1. Capacity Endpoint
```python
# executor-service/app.py
@app.get("/capacity")
async def capacity():
    """Check if executor can accept new tasks"""
    max_concurrent = int(os.getenv("MAX_CONCURRENT_EXECUTIONS", "1"))
    current_running = len(running_containers)
    
    can_accept = current_running < max_concurrent
    
    return {
        "executor_id": executor_id,
        "can_accept": can_accept,
        "running": current_running,
        "max_concurrent": max_concurrent,
        "available_slots": max(0, max_concurrent - current_running)
    }
```

### 2. Worker Checks Capacity First
```python
# celery-worker/tasks.py
# Check for available executor with capacity
executor_url = get_available_executor_url()
if not executor_url:
    # No executor available, retry the task
    logger.info(f"No executor available for {eval_id}, retrying in 5 seconds")
    raise self.retry(countdown=5, max_retries=None)

# Now that we have an executor, update status to provisioning
update_status("provisioning")
```

## The Race Condition

With the current implementation, this can happen:

```
Time | Worker 1           | Worker 2           | Worker 3           | Executor State
-----|-------------------|-------------------|-------------------|---------------
T0   | Check capacity    | Check capacity    | Check capacity    | 0/1 running
T1   | See available     | See available     | See available     | 0/1 running
T2   | Set provisioning  | Set provisioning  | Set provisioning  | 0/1 running
T3   | Submit task ✓     | Submit task ✗     | Submit task ✗     | 1/1 running
```

Workers 2 and 3 fail because the executor is now full.

## Solution Options

### Option 1: Optimistic Concurrency (Recommended)

Let the race happen and handle failures gracefully:

```python
@app.task(bind=True, max_retries=None)
def execute_evaluation(self, eval_id, code, language, priority=False):
    # Try to find an available executor
    executor_url = find_executor_with_capacity()
    
    if not executor_url:
        # No capacity anywhere, retry later
        raise self.retry(countdown=5)
    
    try:
        # Attempt to submit - this is the atomic operation
        response = httpx.post(f"{executor_url}/execute", 
                            json={"eval_id": eval_id, "code": code})
        
        if response.status_code == 200:
            # Success! Now we can set provisioning
            update_status(eval_id, "provisioning")
            return response.json()
        elif response.status_code == 503:
            # Executor is full (lost the race), retry
            raise self.retry(countdown=random.uniform(1, 5))
        else:
            # Actual error
            raise Exception(f"Executor error: {response.status_code}")
            
    except httpx.RequestError:
        # Network error, retry with backoff
        raise self.retry(countdown=min(2 ** self.request.retries, 300))
```

**Pros:**
- Simple and robust
- No distributed locking needed
- Executor service is source of truth
- Natural load balancing through retries

**Cons:**
- Some wasted API calls
- Potential thundering herd

### Option 2: Distributed Semaphore

Use Redis to track executor slots:

```python
class ExecutorSemaphore:
    def __init__(self, redis_client):
        self.redis = redis_client
        
    def acquire_slot(self, executor_id):
        """Try to acquire an executor slot atomically"""
        key = f"executor:{executor_id}:slots"
        
        # Atomic decrement
        remaining = self.redis.decr(key)
        if remaining >= 0:
            return True
        else:
            # No slots, increment back
            self.redis.incr(key)
            return False
            
    def release_slot(self, executor_id):
        """Release an executor slot"""
        key = f"executor:{executor_id}:slots"
        self.redis.incr(key)
```

**Pros:**
- Prevents races at the source
- More efficient (fewer failed attempts)

**Cons:**
- Additional complexity
- Redis becomes critical path
- Need to handle crashed workers (slot leaks)

### Option 3: Queue per Executor

Create separate Celery queues for each executor:

```python
# Route tasks to executor-specific queues
@app.task(queue='executor-1-queue')
def execute_on_executor_1(eval_id, code):
    # This only runs when executor-1 is the target
    submit_to_executor("http://executor-1:8083", eval_id, code)

# Celery worker configuration
# celery -A tasks worker -Q executor-1-queue --concurrency=1
```

**Pros:**
- No race conditions possible
- Natural work distribution
- Kubernetes-like (pod-specific work queues)

**Cons:**
- Queue proliferation
- Complex routing logic
- Less flexible load balancing

### Option 4: Executor Reservation System

Two-phase commit pattern:

```python
# Phase 1: Reserve capacity
reservation = httpx.post(f"{executor_url}/reserve", 
                        json={"eval_id": eval_id, "ttl": 30})

if reservation.status_code == 200:
    reservation_id = reservation.json()["reservation_id"]
    
    # Update status now that we have a reservation
    update_status(eval_id, "provisioning")
    
    # Phase 2: Execute with reservation
    result = httpx.post(f"{executor_url}/execute",
                       json={"reservation_id": reservation_id, 
                             "eval_id": eval_id,
                             "code": code})
```

**Pros:**
- Guaranteed slot allocation
- Can show accurate queue positions

**Cons:**
- Complex implementation
- Need TTL management
- More API calls

## How Kubernetes Handles This

Kubernetes avoids this problem entirely through centralized scheduling:

### 1. Single Scheduler
```go
// Only ONE scheduler makes placement decisions
func (sched *Scheduler) scheduleOne(ctx context.Context) {
    pod := sched.NextPod()
    node := sched.selectNode(pod)
    err := sched.bind(ctx, pod, node)  // Atomic operation
}
```

### 2. Atomic Binding
```go
// The bind operation is atomic at API server level
binding := &v1.Binding{
    ObjectMeta: metav1.ObjectMeta{Name: pod.Name},
    Target: v1.ObjectReference{Name: node},
}
err := client.Pods(ns).Bind(ctx, binding)
```

### 3. Optimistic Concurrency
```go
// ResourceVersion prevents concurrent modifications
if errors.IsConflict(err) {
    // Someone else modified it, retry with fresh data
}
```

### Key Differences
- **Centralized Decision Making**: One scheduler owns all placement
- **Push Model**: Scheduler assigns work to nodes
- **No Polling**: Nodes don't check for work
- **Atomic Operations**: Binding can't partially succeed

## Recommendation

For our current architecture, **Option 1 (Optimistic Concurrency)** is recommended:

1. **Implementation**:
   - Executor returns 503 when at capacity
   - Workers retry with exponential backoff
   - Only set "provisioning" after successful submission

2. **Benefits**:
   - Simple to implement and understand
   - Executor service remains source of truth
   - Naturally handles failures and scaling
   - No additional infrastructure needed

3. **Future Migration Path**:
   - Can evolve to semaphore pattern if needed
   - Can implement reservation system later
   - Compatible with eventual Kubernetes migration

## Implementation Details

### Executor Service Changes
```python
@app.post("/execute")
async def execute(request: ExecuteRequest):
    # Check capacity atomically
    if len(running_containers) >= MAX_CONCURRENT_EXECUTIONS:
        raise HTTPException(
            status_code=503,
            detail="Executor at capacity",
            headers={"Retry-After": "5"}  # Hint to retry in 5 seconds
        )
    
    # Proceed with execution
    container = start_container(...)
    return {"status": "started", "container_id": container.id}
```

### Celery Worker Changes
```python
@app.task(bind=True)
def execute_evaluation(self, eval_id, code, language, priority=False):
    for attempt in range(100):  # Max attempts
        executors = get_all_healthy_executors()
        random.shuffle(executors)  # Distribute load
        
        for executor_url in executors:
            try:
                response = submit_to_executor(executor_url, eval_id, code)
                if response.status_code == 200:
                    # Success!
                    update_status(eval_id, "provisioning")
                    return response.json()
                elif response.status_code == 503:
                    # Executor full, try next
                    continue
            except Exception:
                continue
        
        # All executors full, backoff and retry
        delay = min(2 ** attempt + random.uniform(0, 1), 60)
        time.sleep(delay)
    
    # Max attempts reached
    raise Exception("No executor available after maximum attempts")
```

## Monitoring and Metrics

To ensure the system works well:

1. **Track Metrics**:
   - Task retry count
   - Time spent in "queued" state
   - Executor utilization
   - 503 response rate

2. **Alerts**:
   - High retry rate (> 50%)
   - Tasks queued > 5 minutes
   - All executors at capacity

3. **Dashboards**:
   - Queue depth per status
   - Executor capacity heat map
   - Task throughput graphs

## Conclusion

While Kubernetes uses centralized scheduling to avoid these problems, our distributed approach with optimistic concurrency provides a good balance of simplicity and reliability. The executor service acts as the authoritative source for capacity, and Celery workers handle contention through retries with backoff.

This pattern is well-tested in distributed systems and scales naturally as you add more workers or executors.