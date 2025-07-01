# Celery Worker Service

This service provides distributed task processing for code evaluations using Celery with Redis as the message broker. It includes production-ready features like retry logic, task cancellation, and dead letter queue handling.

## Quick Start

### 1. Start Celery Worker
```bash
# From project root - Celery is now integrated into main docker-compose.yml
docker-compose up -d celery-worker

# Or start everything including 50/50 traffic split
docker-compose up -d
```

### 2. View Flower Dashboard
Open http://localhost:5555 to monitor tasks in real-time

### 3. Test Celery
```bash
# Install test dependencies
pip install celery[redis] httpx

# Run test script
cd celery-worker
python test_celery.py
```

## Architecture

```
API Service → Redis Queue → Celery Worker → Executor Service
                                          ↓
                                    Storage Service
```

## Key Features

- **Distributed Processing**: Scale by adding more workers
- **Priority Queues**: Three levels - high, default, low with strict ordering
- **Retry Logic**: Configurable exponential backoff with jitter
- **Task Cancellation**: Cancel queued or terminate running tasks
- **Dead Letter Queue**: Capture and analyze permanently failed tasks
- **Monitoring**: Real-time visibility via Flower dashboard
- **Non-blocking**: API returns immediately, processing happens async
- **Traffic Splitting**: Gradual migration from legacy queue system

## Configuration

Key environment variables:
- `CELERY_BROKER_URL`: Redis connection for task queue (default: redis://redis:6379/0)
- `CELERY_RESULT_BACKEND`: Redis connection for results 
- `CELERY_CONCURRENCY`: Number of worker processes (default: 2)
- `EXECUTOR_SERVICE_URL`: Comma-separated executor URLs for round-robin distribution
- `STORAGE_SERVICE_URL`: URL of storage service
- `REDIS_URL`: Redis connection for general use
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)

## Tasks

### evaluate_code
Main task for evaluating code submissions.

```python
from tasks import evaluate_code

result = evaluate_code.delay(
    eval_id="abc123",
    code="print('Hello')",
    language="python"
)
```

### cleanup_old_evaluations
Scheduled task that runs hourly to cleanup old data.

### health_check
Simple task for monitoring worker health.

## Retry Logic

The worker implements sophisticated retry logic with exponential backoff:

```python
# Configuration in retry_config.py
RETRY_POLICIES = {
    'default': {
        'max_retries': 3,
        'base_delay': 5,      # 5 seconds
        'exponential_base': 2,
        'max_delay': 300,     # 5 minutes
        'jitter': True
    },
    'network_error': {
        'max_retries': 5,
        'base_delay': 10,
        'exponential_base': 1.5,
        'max_delay': 600
    }
}
```

Retry delays: 5s → 10s → 20s (with jitter to prevent thundering herd)

## Task Cancellation

Cancel tasks via the API:

```bash
# Cancel a queued task
curl -X POST http://localhost:8080/api/eval/{eval_id}/cancel

# Force terminate a running task
curl -X POST http://localhost:8080/api/eval/{eval_id}/cancel?terminate=true
```

States that can be cancelled:
- `PENDING`: Task removed from queue
- `STARTED`: Task terminated (requires terminate=true)
- `RETRY`: Retry chain stopped

## Dead Letter Queue (DLQ)

Failed tasks after all retries are moved to the DLQ for analysis:

```python
# Access DLQ stats
dlq = DeadLetterQueue()
failed_count = dlq.get_queue_size()
failed_tasks = dlq.get_all_tasks()

# Retry a specific failed task
dlq.retry_task(task_id)

# Clear old entries
dlq.clear_old_tasks(days=30)
```

DLQ entries include:
- Original task arguments
- Exception details
- Full traceback
- Retry count
- Failure timestamp

## Priority Queues

Three queue levels with strict priority ordering:

1. **High Priority** (priority=10)
   - Premium users
   - Time-sensitive evaluations
   - Admin tasks

2. **Default Priority** (priority=5)
   - Standard evaluations
   - Normal user submissions

3. **Low Priority** (priority=1)
   - Batch operations
   - Background tasks
   - Non-urgent evaluations

Configure in API request:
```json
{
  "code": "print('Hello')",
  "language": "python",
  "priority": true  // Sets high priority
}
```

## Monitoring

### Flower Dashboard
- Worker status and pool info
- Active tasks
- Task history
- Queue lengths
- Success/failure rates

### Logs
```bash
docker logs crucible-celery-worker -f
```

## Scaling

### Add More Workers
```bash
# Scale horizontally
docker-compose up -d --scale celery-worker=3
```

### Specialized Workers
```bash
# High-priority only worker
docker run -e CELERY_QUEUES=high_priority crucible-celery-worker

# Configure dedicated workers per queue
celery -A tasks worker -Q high_priority -n high-worker@%h
celery -A tasks worker -Q default -n default-worker@%h  
celery -A tasks worker -Q low_priority -n low-worker@%h
```

### Executor Assignment
Workers use round-robin to distribute tasks across available executors:
- Legacy queue → executor-1
- Celery workers → executor-2, executor-3 (round-robin)

## Development

### Local Development
```bash
cd celery-worker
pip install -r requirements.txt

# Start worker locally
CELERY_BROKER_URL=redis://localhost:6380/0 \
celery -A tasks worker --loglevel=info
```

### Adding New Tasks
1. Add task to `tasks.py`
2. Update routing in `celeryconfig.py` if needed
3. Restart workers

## Production Considerations

1. **Persistence**: Redis configured with AOF for durability
2. **Memory**: Monitor Redis memory usage, configure eviction policies
3. **Security**: Tasks run in isolated containers via executor service
4. **Monitoring**: Flower dashboard + Celery status API endpoint
5. **High Availability**: Consider Redis Sentinel for failover
6. **Retry Strategy**: Configure appropriate retry policies per task type
7. **DLQ Management**: Regular review of failed tasks, automated cleanup
8. **Traffic Migration**: Use CELERY_PERCENTAGE to gradually shift traffic

## Troubleshooting

### Worker Not Processing Tasks
1. Check Redis connection: `docker exec crucible-celery-redis redis-cli ping`
2. Check worker logs: `docker logs crucible-celery-worker`
3. Verify queue has tasks: Check Flower dashboard

### Tasks Failing
1. Check task logs in Flower
2. Verify executor service is running
3. Check storage service connectivity

### Memory Issues
1. Monitor Redis memory: `docker exec crucible-redis redis-cli info memory`
2. Adjust `worker_max_tasks_per_child` to restart workers periodically
3. Consider adding Redis eviction policy

### Task Not Found
1. Check if task was routed to correct queue
2. Verify task ID format (should be celery-{eval_id})
3. Check DLQ if task failed permanently

## Migration from Legacy Queue

The platform supports gradual migration from the legacy queue system:

### Traffic Splitting Configuration
```yaml
# Environment variables in docker-compose.yml
CELERY_ENABLED: true      # Enable Celery integration
CELERY_PERCENTAGE: 0.5    # 50% of traffic to Celery

# Migration phases
# Phase 1: CELERY_PERCENTAGE=0.1  (10% testing)
# Phase 2: CELERY_PERCENTAGE=0.5  (50% validation)
# Phase 3: CELERY_PERCENTAGE=0.9  (90% migration)
# Phase 4: CELERY_PERCENTAGE=1.0  (100% complete)
```

### Monitoring During Migration
1. Compare completion rates between systems
2. Monitor latency differences
3. Track error rates
4. Validate output consistency

### Rollback Strategy
```bash
# Immediate rollback
export CELERY_PERCENTAGE=0
docker-compose restart api-service

# Or force legacy queue
export FORCE_LEGACY_QUEUE=true
```

For detailed migration strategy, see `/docs/architecture/celery-migration-strategy.md`