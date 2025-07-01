# Celery Priority Queues: A Comprehensive Guide

## Overview

Celery's priority queue system is more nuanced than "bigger number = higher priority". It uses a combination of **multiple queues** and **priority values** to achieve sophisticated task routing and ordering.

## Key Concepts

### 1. Queues vs Priority

Celery has two levels of prioritization:

1. **Queue-level priority**: Different queues with different priorities
2. **Task-level priority**: Priority values within a single queue

```python
# Queue configuration with priorities
Queue('high_priority', Exchange('tasks'), routing_key='high', priority=10),
Queue('normal', Exchange('tasks'), routing_key='normal', priority=5),
Queue('low_priority', Exchange('tasks'), routing_key='low', priority=1),
```

### 2. How Priority Works

#### Redis Backend
- Redis doesn't support true priority queues natively
- Celery implements priority using **sorted sets** (ZSET)
- **LOWER numbers = HIGHER priority** (counterintuitive!)
- Priority range: 0-9 (0 is highest, 9 is lowest)

#### RabbitMQ Backend
- Native priority queue support
- **HIGHER numbers = HIGHER priority**
- Priority range: 0-255

## Our Implementation

### Queue Structure

```python
# From celeryconfig.py
task_queues = (
    Queue('evaluation', default_exchange, routing_key='evaluation', priority=5),
    Queue('high_priority', default_exchange, routing_key='high_priority', priority=10),
    Queue('batch', default_exchange, routing_key='batch', priority=1),
    Queue('maintenance', default_exchange, routing_key='maintenance', priority=0),
)
```

### Worker Configuration

```bash
# Worker listens to queues in order of importance
celery -A tasks worker -Q high_priority,evaluation,batch,maintenance
```

The order matters! The worker will:
1. Check `high_priority` queue first
2. Only check `evaluation` if `high_priority` is empty
3. Continue down the list

### Task Routing

```python
# API submits to different queues based on priority flag
if request.priority:
    queue = 'high_priority'
else:
    queue = 'evaluation'

celery_app.send_task(
    'tasks.evaluate_code',
    args=[eval_id, code, language],
    queue=queue
)
```

## Priority Strategies

### 1. Multiple Queues (Recommended)
```python
# Separate queues for different priority levels
- high_priority: Urgent tasks
- evaluation: Normal tasks
- batch: Bulk operations
- maintenance: Background cleanup
```

**Pros:**
- Clear separation of concerns
- Easy to monitor and scale
- Workers can be dedicated to specific queues

**Cons:**
- More complex configuration
- Potential for queue starvation

### 2. Single Queue with Priority Values
```python
# All tasks in one queue with different priorities
result = celery_app.send_task(
    'tasks.evaluate_code',
    args=[eval_id, code],
    priority=0  # 0-9, lower is higher priority
)
```

**Pros:**
- Simpler configuration
- No queue starvation

**Cons:**
- Less control over task distribution
- Harder to monitor priority effectiveness

### 3. Hybrid Approach (Our Choice)
```python
# Multiple queues + priority values within queues
# High-priority queue for urgent tasks
# Normal queue with priority values for fine-grained control
```

## Best Practices

### 1. Prevent Queue Starvation
```python
# Use worker concurrency to ensure all queues get processed
celery worker -Q high_priority,normal,low --concurrency=4
# 2 workers for high_priority, 1 for normal, 1 for low
```

### 2. Monitor Queue Lengths
```python
# Check queue depths regularly
from celery import current_app

def get_queue_length(queue_name):
    with current_app.connection_or_acquire() as conn:
        return conn.default_channel.queue_declare(
            queue=queue_name, passive=True
        ).message_count
```

### 3. Set Appropriate Timeouts
```python
# Prevent high-priority tasks from blocking forever
task_time_limit = 300  # 5 minutes hard limit
task_soft_time_limit = 240  # 4 minutes soft limit
```

### 4. Use Priority Sparingly
```python
# Reserve high priority for truly urgent tasks
# Most tasks should use normal priority
if user.is_premium and task.is_urgent:
    priority = True
else:
    priority = False
```

## Common Pitfalls

### 1. Priority Inversion
High-priority tasks waiting for resources held by low-priority tasks:
```python
# Bad: High-priority task depends on low-priority result
@app.task(queue='high_priority')
def urgent_task():
    result = slow_task.delay().get()  # This blocks!
    
# Good: Use callbacks or separate tasks
@app.task(queue='high_priority')
def urgent_task():
    slow_task.apply_async(link=process_result.s())
```

### 2. Queue Configuration Mismatch
```python
# Worker not listening to all queues
celery worker -Q normal  # Misses high_priority!

# Always specify all queues or use default
celery worker -Q high_priority,normal,low
```

### 3. Forgetting Redis Limitations
```python
# Redis: 0 is highest priority
task.apply_async(priority=0)  # Urgent

# RabbitMQ: 255 is highest priority  
task.apply_async(priority=255)  # Urgent
```

## Monitoring and Debugging

### Using Flower
```python
# Flower shows queue lengths and task distribution
# Access at http://localhost:5555
# Monitor:
# - Queue lengths
# - Task execution times by queue
# - Worker utilization
```

### Logging Queue Selection
```python
@app.task(bind=True)
def evaluate_code(self, eval_id, code, language):
    logger.info(f"Task {self.request.id} in queue {self.request.queue}")
    # Process task...
```

### Metrics to Track
1. **Queue depth**: How many tasks waiting
2. **Wait time**: Time from submission to execution
3. **Execution time**: How long tasks take
4. **Throughput**: Tasks/second by queue

## Example: E-commerce Order Processing

```python
# Configure queues for different order types
task_queues = (
    Queue('payment_failed', priority=10),    # Highest - fix payment issues
    Queue('express_orders', priority=8),     # High - paid for fast delivery
    Queue('normal_orders', priority=5),      # Normal - standard orders
    Queue('reports', priority=1),            # Low - analytics
)

# Route tasks based on business logic
def submit_order(order):
    if order.payment_status == 'failed':
        queue = 'payment_failed'
    elif order.shipping_type == 'express':
        queue = 'express_orders'
    else:
        queue = 'normal_orders'
    
    process_order.apply_async(args=[order.id], queue=queue)
```

## Testing Priority Queues

```python
import time
from celery import group

def test_priority_ordering():
    # Submit low priority tasks first
    low_tasks = group(
        slow_task.s().set(queue='low_priority') 
        for _ in range(10)
    )
    low_tasks.apply_async()
    
    # Then submit high priority
    time.sleep(0.1)
    high_task = urgent_task.apply_async(queue='high_priority')
    
    # High priority should complete first
    assert high_task.get(timeout=5) == 'completed'
```

## Conclusion

Celery priority queues are powerful but require careful design:

1. **Use multiple queues** for clear task separation
2. **Order matters** when workers consume from queues  
3. **Monitor queue depths** to prevent starvation
4. **Test thoroughly** to ensure priority behavior
5. **Document your priority scheme** for team understanding

Remember: Priority queues are not a silver bullet. They're best used when you have genuinely different classes of tasks with different urgency levels.