# Celery Integration Overview

## Table of Contents
1. [How Celery Integration Works](#how-celery-integration-works)
2. [Primer on celery_client.py](#primer-on-celery_clientpy)
3. [Future State Architecture](#future-state-architecture)
4. [Current Implementation Reality](#current-implementation-reality)
5. [Architecture Flows](#architecture-flows)
6. [Celery Communication Architecture](#celery-communication-architecture)
7. [Redis Commands Explained](#redis-commands-explained)
8. [What Celery Adds to Redis](#what-celery-adds-to-redis)

## How Celery Integration Works

### Current Flow (Without Celery)
```
User → API → Queue Service → Redis Queue → Queue Worker → Executor
```

### Dual-Write Flow (During Migration)
```
User → API → Queue Service → Redis Queue → Queue Worker → Executor
         ↓
         └→ Celery → Celery Redis → Celery Worker → Executor
```

### The Integration Points

1. **In `celery_client.py`** - A lightweight module that:
   - Creates a minimal Celery app just for submitting tasks
   - Doesn't need the full worker code
   - Can be enabled/disabled with environment variable
   - Submits tasks without blocking the API

2. **In the API's `/api/eval` endpoint**:
   ```python
   # Existing code submits to queue service
   response = await client.post(f"{QUEUE_SERVICE_URL}/tasks", ...)
   
   # New code ALSO submits to Celery (if enabled)
   celery_task_id = submit_evaluation_to_celery(...)
   ```

3. **Key Features**:
   - **Non-blocking**: Celery submission happens in background
   - **Fault tolerant**: If Celery fails, the old system still works
   - **Feature flag**: `CELERY_ENABLED=true` turns it on
   - **Same eval_id**: Both systems use the same ID for tracking

4. **Environment Variables**:
   ```yaml
   api-service:
     environment:
       - CELERY_ENABLED=false  # Start with false
       - CELERY_BROKER_URL=redis://celery-redis:6379/0
   ```

5. **Monitoring**:
   - Health endpoint shows Celery status
   - Can see if workers are connected
   - Flower dashboard for detailed monitoring

### Why This Works Well

1. **Zero Risk**: Old system untouched
2. **Gradual Migration**: Can test with small % of traffic
3. **Easy Rollback**: Just set `CELERY_ENABLED=false`
4. **Same API**: Frontend doesn't need changes
5. **Parallel Validation**: Can compare results from both systems

The beauty is that we're not replacing anything - we're adding Celery alongside the existing system until we're confident it works perfectly.

## Primer on celery_client.py

### Purpose
The `celery_client.py` module allows the API service to submit tasks to Celery **without** importing the full worker code. It's a lightweight client that only knows how to send messages to Celery's queue.

### Key Concepts

#### 1. Minimal Celery App
```python
celery_app = Celery('crucible_api', broker=CELERY_BROKER_URL)
```
- Creates a Celery instance just for sending tasks
- Only needs to know the broker URL (Redis)
- Doesn't import any task functions

#### 2. Feature Flag Pattern
```python
CELERY_ENABLED = os.environ.get('CELERY_ENABLED', 'false').lower() == 'true'
```
- Controlled by environment variable
- Allows gradual rollout
- Easy to disable if issues arise

#### 3. send_task() Method
```python
result = celery_app.send_task(
    'tasks.evaluate_code',  # Task name as string
    args=[eval_id, code, language],
    queue='evaluation'
)
```
This is the key insight:
- Uses task name as a **string** not an import
- API doesn't need worker code
- Worker registers tasks with these names
- Celery routes by name matching

#### 4. Non-blocking Submission
```python
def submit_evaluation_to_celery(...) -> Optional[str]:
    if not CELERY_ENABLED:
        return None  # Graceful degradation
    
    try:
        result = celery_app.send_task(...)
        return result.id
    except Exception:
        return None  # Don't fail the API call
```
- Returns immediately
- Errors don't break the API
- Returns task ID for tracking

### Why This Design?

1. **Separation of Concerns**
   - API service doesn't need executor logic
   - Worker doesn't need API logic
   - Clean boundaries

2. **Lightweight Dependencies**
   - API only needs `celery` package
   - Not the full worker environment

3. **Fault Isolation**
   - If Celery is down, API still works
   - If worker code has bugs, API unaffected

4. **Gradual Migration**
   - Can test with 1% of traffic
   - Compare results between systems
   - Roll back instantly

### Usage in API

In the API endpoint:
```python
# Existing code (unchanged)
await client.post(f"{QUEUE_SERVICE_URL}/tasks", ...)

# New code (added)
celery_task_id = submit_evaluation_to_celery(
    eval_id=eval_id,
    code=request.code,
    language=request.language
)

if celery_task_id:
    logger.info(f"Also submitted to Celery: {celery_task_id}")
```

### The Magic of Task Names

When the worker starts:
```python
# In tasks.py
@app.task
def evaluate_code(eval_id, code, language):
    # This registers as 'tasks.evaluate_code'
```

When API sends:
```python
# In celery_client.py
celery_app.send_task('tasks.evaluate_code', ...)
```

Celery matches these by name - no direct code connection needed!

This pattern is common in microservices - services communicate through contracts (task names) not shared code.

## Future State Architecture

### Why Keep celery_client.py Separate

1. **Single Responsibility Principle**
   ```python
   # celery_client.py - Only knows about Celery
   # microservices_gateway.py - Only knows about HTTP routing
   ```

2. **Easier Testing**
   ```python
   # Can mock just the Celery client
   from unittest.mock import patch
   
   @patch('app.celery_client.submit_evaluation_to_celery')
   def test_api_endpoint(mock_celery):
       mock_celery.return_value = "task-123"
       # Test API without Celery
   ```

3. **Reusability**
   - Other services might need Celery client
   - Admin tools could import it
   - CLI scripts can use it

### What Changes When Fully on Celery

**Before (Dual-Write):**
```python
# In microservices_gateway.py
# Forward to queue service (primary)
response = await client.post(f"{QUEUE_SERVICE_URL}/tasks", ...)

# Also submit to Celery (shadow)
celery_task_id = submit_evaluation_to_celery(...)
```

**After (Celery Only):**
```python
# In microservices_gateway.py
# Only submit to Celery
celery_task_id = submit_evaluation_to_celery(
    eval_id=eval_id,
    code=request.code,
    language=request.language,
    priority=check_user_tier(request.user)
)

if not celery_task_id:
    raise HTTPException(503, "Task submission failed")

# No more queue service call!
```

### Enhanced celery_client.py for Production

```python
# celery_client.py in full production mode
class CeleryClient:
    def __init__(self):
        self.app = Celery('crucible', broker=CELERY_BROKER_URL)
        self.initialize_monitoring()
    
    def submit_evaluation(self, eval_id: str, code: str, 
                         language: str, priority: int = 5) -> str:
        """Submit with priority queues"""
        queue = self._select_queue(priority)
        
        result = self.app.send_task(
            'tasks.evaluate_code',
            args=[eval_id, code, language],
            queue=queue,
            priority=priority,
            task_id=f"eval-{eval_id}"
        )
        
        self.metrics.task_submitted(queue=queue)
        return result.id
    
    def cancel_evaluation(self, task_id: str) -> bool:
        """Cancel running evaluation"""
        self.app.control.revoke(task_id, terminate=True)
        return True
    
    def get_queue_stats(self) -> dict:
        """Get real-time queue statistics"""
        inspect = self.app.control.inspect()
        return {
            'active': len(inspect.active() or {}),
            'reserved': len(inspect.reserved() or {}),
            'stats': inspect.stats()
        }
```

### Benefits of Keeping It Separate

1. **Clean Architecture**
   - Gateway handles HTTP concerns
   - Celery client handles task concerns
   - Clear boundaries

2. **Future Flexibility**
   - Easy to switch to RabbitMQ
   - Can add new task types
   - Can enhance without touching API

3. **Monitoring Integration**
   ```python
   # Easy to add metrics to one place
   class CeleryClient:
       def submit_evaluation(self, ...):
           start = time.time()
           result = self._submit()
           self.metrics.submission_time(time.time() - start)
   ```

### What Gets Removed

When fully on Celery:
- Remove `queue-worker` service
- Remove old Redis queue
- Remove queue service HTTP calls
- Remove dual-write logic

But `celery_client.py` stays and might even grow with features like:
- Task cancellation
- Priority management
- Queue routing logic
- Monitoring/metrics
- Circuit breakers

Think of it as your "Celery SDK" - a clean interface between your application and the task queue system.

## Current Implementation Reality

You're absolutely correct! I apologize for the confusion. Looking at the code:

```python
# Simple in-memory queue (deque for FIFO behavior)
task_queue = deque()
```

The current implementation uses a **Python `deque`** (double-ended queue), not Redis for the actual task queue.

Here's what's actually happening:
- **Queue Service**: Uses an in-memory `deque` for task storage
- **Redis**: Only used for event publishing/subscribing, NOT for the queue itself

So my statements about "replacing Redis queue with Celery" were incorrect. We're actually:
- **Current**: Python `deque` in queue-service (in-memory, single instance)
- **Future**: Celery with Redis as broker (distributed, persistent)

This makes the migration even more important because:
1. **Current `deque`** loses all tasks if service restarts
2. **No persistence** - tasks vanish on crash
3. **Can't scale** - only one queue-service instance
4. **No priority** - just FIFO order

The Celery migration will be a huge upgrade from the current simple in-memory queue.

## Architecture Flows

### Current Flow (HTTP-based)
```
User HTTP Request
    ↓
API Service (port 8000)
    ↓ (HTTP POST)
Queue Service (port 8002)
    ↓ (stores in memory)
Python deque()
    ↓ (HTTP GET polling)
Queue Worker
    ↓ (HTTP POST)
Executor Service
```

**Everything is HTTP calls between services**

### New Celery Flow (Message-based)
```
User HTTP Request
    ↓
API Service (port 8000)
    ↓ (Redis Protocol on port 6379)
Celery Redis
    ↓ (Redis Protocol)
Celery Worker
    ↓ (HTTP POST)
Executor Service
```

**Key differences:**

1. **Protocol Change**: 
   - Before: HTTP everywhere
   - After: Redis protocol for queueing

2. **Where Tasks are Created**:
   - Before: API makes HTTP call, queue-service creates task
   - After: API directly creates Celery task using Redis protocol

3. **No More Queue Service**:
   - Before: Need queue-service to manage deque
   - After: Redis IS the queue

4. **Port Usage**:
   - Before: HTTP on 8002 for queue-service
   - After: Redis protocol on 6379 (or 6380 for Celery Redis)

The beauty is that Celery handles all the Redis protocol details. From the API's perspective, it's just:
```python
# Instead of HTTP call
# response = await client.post("http://queue:8002/tasks", json={...})

# Direct to Redis via Celery
result = celery_app.send_task('tasks.evaluate_code', args=[...])
```

Much more efficient - no HTTP overhead for queueing!

## Celery Communication Architecture

### 1. API → Redis (via Celery Client)
```python
# When API calls send_task()
celery_app.send_task('tasks.evaluate_code', args=[...], queue='evaluation')
```
This actually:
- Serializes the task as JSON
- Pushes to Redis LIST: `celery:queue:evaluation`
- Returns immediately (fire-and-forget)

### 2. Inside Redis (The Channels)
```
Redis Database:
├── celery:queue:evaluation      # Normal priority tasks
├── celery:queue:high_priority   # High priority tasks  
├── celery:queue:batch          # Batch processing tasks
├── celery:queue:maintenance    # Cleanup tasks
├── celery:unacked             # Tasks being processed
├── celery:results:task-123    # Task results
└── celery:events              # Real-time events
```

### 3. Celery Workers → Redis
Workers continuously:
```python
# Simplified version of what Celery does internally:
while True:
    # BRPOP blocks until task available
    task = redis.brpop(['celery:queue:high_priority', 
                       'celery:queue:evaluation',
                       'celery:queue:batch'], timeout=1)
    
    if task:
        # Move to "unacked" queue (for reliability)
        redis.lpush('celery:unacked', task)
        
        # Process the task
        result = execute_task(task)
        
        # Store result
        redis.setex(f'celery:results:{task.id}', 3600, result)
        
        # Remove from unacked
        redis.lrem('celery:unacked', task)
```

### 4. The Event System (Monitoring)
```python
# Workers publish events
redis.publish('celery:events', {
    'type': 'task-started',
    'task_id': 'eval-123',
    'worker': 'worker-1',
    'timestamp': '2024-01-20T10:00:00Z'
})

# Flower subscribes to these events
redis.subscribe('celery:events')  # Real-time monitoring
```

### 5. Priority Queue Magic
Celery uses Redis's blocking pop with multiple queues:
```
# Check queues in priority order
BRPOP celery:queue:high_priority celery:queue:evaluation celery:queue:batch
```
- Checks high_priority first
- Only checks evaluation if high_priority empty
- Only checks batch if both above empty

### The Full Picture
```
┌─────────────┐
│ API Service │
│ (send_task) │
└──────┬──────┘
       │ LPUSH
       ↓
┌─────────────────────────────────────┐
│          Redis Broker               │
│ ┌─────────────┐ ┌─────────────┐    │
│ │ Queue:high  │ │ Queue:eval  │    │
│ └─────────────┘ └─────────────┘    │
│ ┌─────────────┐ ┌─────────────┐    │
│ │   Events    │ │   Results   │    │
│ └─────────────┘ └─────────────┘    │
└────┬────────────────┬───────────────┘
     │ BRPOP          │ SUBSCRIBE
     ↓                ↓
┌──────────┐    ┌──────────┐
│ Worker 1 │    │  Flower  │
│ Worker 2 │    │ Monitor  │
│ Worker N │    └──────────┘
└──────────┘
```

### Why This is Better Than HTTP Queue

1. **Atomic Operations**: Redis BRPOP is atomic - no race conditions
2. **Blocking Waits**: Workers sleep until work arrives (no polling)
3. **Built-in Priority**: Just check queues in order
4. **Reliability**: "unacked" queue handles worker crashes
5. **Visibility**: Event stream shows everything happening

The key insight: Celery doesn't talk to a "Celery server" - it talks directly to Redis, which acts as the message broker. The workers are just processes reading from Redis!

## Redis Commands Explained

### LPUSH (Left Push)
```python
# Adds item to the LEFT (front) of a list
redis.LPUSH("myqueue", "task1")  # Queue: [task1]
redis.LPUSH("myqueue", "task2")  # Queue: [task2, task1]
redis.LPUSH("myqueue", "task3")  # Queue: [task3, task2, task1]
```

### BRPOP (Blocking Right Pop)
```python
# Takes item from the RIGHT (back) of list
# BLOCKS (waits) if list is empty!
task = redis.BRPOP("myqueue", timeout=30)  # Gets: task1
# Queue now: [task3, task2]

# If queue empty, it WAITS up to 30 seconds
# This is why workers don't need to poll!
```

So together: LPUSH + BRPOP = FIFO Queue (First In, First Out)

## Celery Without Redis/Broker?

You're right - Celery **always needs a message broker**. When I said "Redis isn't essential", I meant you can use OTHER brokers:

### Option 1: RabbitMQ (Different broker)
```python
# Instead of Redis
celery_app = Celery('app', broker='amqp://guest@rabbit:5672//')
```
RabbitMQ uses AMQP protocol, not Redis commands

### Option 2: Amazon SQS (Cloud broker)
```python
celery_app = Celery('app', broker='sqs://KEYID:SECRET@')
```
Uses AWS API calls, not Redis

### Option 3: "Eager" Mode (NO BROKER - Testing Only!)
```python
# celeryconfig.py
task_always_eager = True  # Tasks execute immediately, synchronously
```

With eager mode:
```python
# This normally queues a task:
result = evaluate_code.delay(eval_id, code)

# But with eager mode, it runs RIGHT NOW in the same process!
# No queue, no workers, no async - just a function call
```

### What Eager Mode Looks Like

**Normal Celery:**
```
API Process          Redis           Worker Process
    |                 |                   |
    |--send_task-->   |                   |
    |                 |<--BRPOP-----------|
    |                 |                   |
    |                 |---task_data------>|
                                          |
                                     (executes)
```

**Eager Mode:**
```
API Process
    |
    |--evaluate_code.delay()
    |
    v
(executes immediately in API process)
    |
    v
(returns result)
```

### Why You NEED a Broker in Production

Without a broker, you lose:
1. **Async execution** - Everything blocks
2. **Distributed processing** - Can't scale workers
3. **Reliability** - Tasks lost on crash
4. **Monitoring** - No queue visibility
5. **Priority/Routing** - No task organization

Think of it like email:
- **Broker (Redis)** = Email server
- **send_task()** = Send email
- **Workers** = People reading emails
- **Eager mode** = Just yelling across the room!

So Celery always needs SOME broker - Redis is just the simplest option. The broker IS the queue.

## What Celery Adds to Redis

Since Redis already has queues (lists) and pub/sub, what exactly does Celery add?

### What Raw Redis Gives You
```python
# You COULD just use Redis directly:
redis.lpush("tasks", json.dumps({"eval_id": "123", "code": "print()"}))
task = redis.brpop("tasks")
data = json.loads(task)
# Now what? How do you execute it?
```

### What Celery Adds on Top

#### 1. Task Registry & Routing
```python
# Celery knows what function to call
@app.task
def evaluate_code(eval_id, code):  # Registered as 'tasks.evaluate_code'
    ...

# When message arrives, Celery:
# - Deserializes the message
# - Looks up 'tasks.evaluate_code' in registry
# - Calls the actual Python function
```

#### 2. Serialization Protocol
```python
# Raw Redis - you handle everything:
redis.lpush("queue", json.dumps({
    "function": "evaluate_code",
    "args": ["123", "print()"],
    "kwargs": {},
    "id": "abc-def",
    "retries": 0
}))

# Celery - handles all serialization:
evaluate_code.delay("123", "print()")  # That's it!
```

#### 3. Result Management
```python
# Celery automatically:
# - Stores results in Redis
# - Tracks task state (PENDING → STARTED → SUCCESS/FAILURE)
# - Handles result expiration
# - Provides result retrieval API

result = evaluate_code.delay("123", "print()")
print(result.state)  # "PENDING"
# ... later ...
print(result.state)  # "SUCCESS"
print(result.result) # Actual return value
```

#### 4. Retry Logic
```python
@app.task(bind=True, max_retries=3)
def evaluate_code(self, eval_id, code):
    try:
        # do work
    except NetworkError as exc:
        # Celery handles exponential backoff, retry tracking
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

#### 5. Worker Pool Management
```bash
# Celery manages:
# - Multiple worker processes
# - Prefork vs threads vs gevent
# - Memory limits per worker
# - Automatic worker restart

celery worker -c 4  # 4 parallel workers, Celery handles distribution
```

#### 6. Task Lifecycle Hooks
```python
@task_prerun.connect
def task_prerun_handler(task_id, task, **kwargs):
    # Before any task runs
    
@task_success.connect
def task_success_handler(result, **kwargs):
    # After successful completion

@task_failure.connect
def task_failure_handler(exception, **kwargs):
    # On task failure
```

#### 7. Complex Workflows
```python
# Chain tasks
chain(
    evaluate_code.s("123", "print('step 1')"),
    process_results.s(),
    send_notification.s()
).apply_async()

# Group parallel tasks
group(
    evaluate_code.s("1", code),
    evaluate_code.s("2", code),
    evaluate_code.s("3", code)
).apply_async()
```

#### 8. Monitoring & Visibility
```python
# Celery publishes events to Redis channels:
# - task-sent
# - task-received  
# - task-started
# - task-succeeded
# - task-failed
# - worker-online
# - worker-heartbeat

# Flower subscribes to these for monitoring
```

### The Complete Picture

What You Write:
```python
evaluate_code.delay("123", "print()")
```

What Actually Happens:
1. Celery creates message with metadata
2. Serializes with MessagePack/JSON
3. LPUSH to redis://celery:queue:evaluation
4. Worker BRPOP from queues in priority order
5. Celery deserializes message
6. Looks up task in registry
7. Executes with retry/timeout handling
8. Stores result in Redis
9. Publishes events for monitoring
10. Manages worker lifecycle

**Think of it this way:**
- **Redis** = Raw TCP/IP networking
- **Celery** = HTTP protocol on top

Redis gives you the transport, Celery gives you the application protocol!