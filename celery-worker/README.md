# Celery Worker Service

This service provides distributed task processing for code evaluations using Celery with Redis as the message broker.

## Quick Start

### 1. Start Celery Services
```bash
# From project root
docker-compose -f docker-compose.yml -f docker-compose.celery.yml up -d
```

### 2. View Flower Dashboard
Open http://localhost:5555 (login: admin/crucible)

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
- **Priority Queues**: High priority for premium users
- **Retry Logic**: Automatic retry with exponential backoff
- **Monitoring**: Real-time visibility via Flower
- **Non-blocking**: API returns immediately, processing happens async

## Configuration

Key environment variables:
- `CELERY_BROKER_URL`: Redis connection for task queue
- `CELERY_RESULT_BACKEND`: Redis connection for results
- `CELERY_CONCURRENCY`: Number of worker processes (default: 4)
- `EXECUTOR_SERVICE_URL`: URL of executor service
- `STORAGE_SERVICE_URL`: URL of storage service

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
docker-compose -f docker-compose.yml -f docker-compose.celery.yml \
  scale celery-worker=3
```

### Specialized Workers
```yaml
# High-priority worker
celery -A tasks worker -Q high_priority -c 2

# Batch processing worker  
celery -A tasks worker -Q batch -c 1
```

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
2. **Memory**: Redis limited to 256MB with LRU eviction
3. **Security**: Non-root user in container
4. **Monitoring**: Integrate with Prometheus (future)
5. **High Availability**: Consider Redis Sentinel (future)

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
1. Monitor Redis memory: `docker exec crucible-celery-redis redis-cli info memory`
2. Adjust `worker_max_tasks_per_child` to restart workers periodically
3. Consider adding Redis eviction policy