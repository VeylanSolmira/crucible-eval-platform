# Dead Letter Queue (DLQ) Implementation

## Overview

The Dead Letter Queue (DLQ) is a critical component for handling permanently failed tasks in our Celery-based evaluation system. It provides visibility into failures, enables manual intervention, and prevents task loss.

## Architecture

### Components

```
┌─────────────┐     Failed after      ┌─────────────┐
│   Celery    │     max retries       │     DLQ     │
│   Worker    │ ──────────────────▶   │   (Redis)   │
└─────────────┘                       └─────────────┘
                                             │
                                             ▼
                                      ┌─────────────┐
                                      │   DLQ API   │
                                      │  Endpoints  │
                                      └─────────────┘
```

### Storage

DLQ uses Redis for storage with two data structures:
1. **Queue List** (`celery:dlq`) - FIFO queue of failed tasks
2. **Metadata Hash** (`celery:dlq:metadata:{task_id}`) - Quick lookup

## When Tasks Enter DLQ

Tasks are added to DLQ when:
1. Task has failed after `max_retries` attempts (default: 5)
2. Non-retryable exception occurs (e.g., invalid code syntax)
3. Manual DLQ addition for investigation

## DLQ Task Structure

```python
@dataclass
class DeadLetterTask:
    task_id: str              # Celery task ID
    task_name: str            # e.g., "evaluate_code"
    eval_id: str              # Our evaluation ID
    args: List[Any]           # Original arguments
    kwargs: Dict[str, Any]    # Original kwargs
    exception_class: str      # e.g., "HTTPError"
    exception_message: str    # Error details
    traceback: str            # Full stack trace
    retry_count: int          # How many retries attempted
    first_failure_time: datetime
    last_failure_time: datetime
    metadata: Dict[str, Any]  # Additional context
```

## API Endpoints

### List DLQ Tasks
```http
GET /api/dlq/tasks?limit=100&offset=0&eval_id=xxx
```

Response:
```json
[
  {
    "task_id": "celery-eval-123",
    "eval_id": "eval-123",
    "task_name": "evaluate_code",
    "exception_class": "HTTPError",
    "retry_count": 5,
    "added_at": "2024-01-20T10:30:00Z"
  }
]
```

### Get DLQ Statistics
```http
GET /api/dlq/statistics
```

Response:
```json
{
  "queue_size": 42,
  "exception_breakdown": {
    "HTTPError": 15,
    "TimeoutError": 10,
    "ConnectionError": 17
  },
  "task_breakdown": {
    "evaluate_code": 40,
    "cleanup_old_evaluations": 2
  },
  "sample_size": 42
}
```

### Get Task Details
```http
GET /api/dlq/tasks/{task_id}
```

### Retry Task
```http
POST /api/dlq/tasks/{task_id}/retry
```

This removes the task from DLQ and resubmits it to Celery.

### Remove Task
```http
DELETE /api/dlq/tasks/{task_id}
```

Permanently removes a task from DLQ.

### Batch Retry
```http
POST /api/dlq/tasks/retry-batch

{
  "task_ids": ["task-1", "task-2", "task-3"]
}
```

## Monitoring

### Scheduled Monitor Task
```python
@app.task
def monitor_dead_letter_queue():
    """Runs every 30 minutes via Celery Beat."""
    stats = dlq.get_statistics()
    
    # Alert if queue is growing
    if stats['queue_size'] > 100:
        alert_ops_team(f"DLQ has {stats['queue_size']} failed tasks")
    
    # Check for error patterns
    for exc_type, count in stats['exception_breakdown'].items():
        if count > 10:
            logger.warning(f"High frequency of {exc_type}: {count}")
```

### Metrics to Track
- Queue size over time
- Error type distribution
- Task type distribution
- Retry success rate
- Time in queue before retry/removal

## Operations Playbook

### Common Scenarios

#### 1. Executor Service Down
**Symptoms**: Many HTTPError/ConnectionError in DLQ
**Action**:
1. Fix executor service
2. Batch retry affected tasks
3. Monitor retry success

#### 2. Bad Code Pattern
**Symptoms**: Same exception for multiple evaluations
**Action**:
1. Identify pattern in failed code
2. Fix issue (if platform bug)
3. Notify users (if user error)
4. Retry or remove tasks

#### 3. Resource Exhaustion
**Symptoms**: Timeout errors in DLQ
**Action**:
1. Check container resource limits
2. Increase limits if needed
3. Retry affected tasks

### Manual Investigation
```python
# Connect to Redis
redis-cli

# View queue size
LLEN celery:dlq

# View first task
LINDEX celery:dlq 0

# Search metadata
KEYS celery:dlq:metadata:*
```

## Best Practices

### 1. Regular Monitoring
- Check DLQ size daily
- Investigate error patterns
- Clean up resolved tasks

### 2. Retention Policy
- Keep tasks for 30 days by default
- Archive important failures
- Auto-cleanup very old tasks

### 3. Alerting Thresholds
- Queue size > 100: Investigation needed
- Queue size > 500: Immediate action
- Single error type > 50: Pattern analysis

### 4. Retry Strategy
- Verify issue is resolved before retry
- Use batch retry for systemic issues
- Monitor retry success rate

## Security Considerations

### Access Control
- DLQ endpoints require admin privileges
- Task details may contain sensitive code
- Implement audit logging for DLQ operations

### Data Privacy
- Code snippets in metadata are truncated
- PII should not be stored in DLQ
- Regular cleanup prevents data accumulation

## Future Enhancements

### 1. Auto-Retry Logic
```python
# Retry tasks that failed due to transient errors
if task.exception_class in TRANSIENT_ERRORS:
    if task.age < timedelta(hours=1):
        retry_task(task.task_id)
```

### 2. Pattern Detection
- ML-based error classification
- Automatic root cause analysis
- Predictive failure alerts

### 3. Self-Healing
- Automatic service restart on failures
- Dynamic resource allocation
- Circuit breaker integration

## Integration with Monitoring

### Prometheus Metrics
```python
dlq_size = Gauge('celery_dlq_size', 'Number of tasks in DLQ')
dlq_additions = Counter('celery_dlq_additions_total', 'Tasks added to DLQ')
dlq_retries = Counter('celery_dlq_retries_total', 'Tasks retried from DLQ')
```

### Grafana Dashboard
- DLQ size over time
- Error type breakdown pie chart
- Retry success rate
- Task age distribution

## Interview Discussion Points

1. **Why use DLQ instead of infinite retries?**
   - Prevents resource exhaustion
   - Enables human investigation
   - Identifies systemic issues
   - Maintains system stability

2. **Why Redis for DLQ storage?**
   - Already used for Celery broker
   - Fast access for monitoring
   - TTL support for auto-cleanup
   - Atomic operations

3. **Alternative approaches?**
   - Database table (more durable, slower)
   - S3 bucket (long-term archive)
   - Dedicated queue service (SQS DLQ)
   - Elasticsearch (better search)

4. **How to prevent DLQ growth?**
   - Fix root causes quickly
   - Implement circuit breakers
   - Better error categorization
   - Proactive monitoring