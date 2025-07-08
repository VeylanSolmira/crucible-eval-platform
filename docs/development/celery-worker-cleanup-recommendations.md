# Celery Worker Cleanup Recommendations

## Summary
The celery-worker directory contains several unused or legacy files that should be cleaned up for better maintainability.

## Immediate Actions

### 1. Remove Unused Files
```bash
# Remove unused files
rm celery-worker/celerybeat-schedule     # Artifact from celerybeat that isn't running
rm celery-worker/task_management.py      # Unused module
rm celery-worker/executor_router.py      # Legacy code replaced by executor_pool.py
```

### 2. Decide on Celery Beat
Either:
- **Option A**: Remove beat schedule from `celeryconfig.py` if cleanup isn't needed
- **Option B**: Add celerybeat service to docker-compose.yml:
```yaml
celery-beat:
  build:
    context: .
    dockerfile: celery-worker/Dockerfile
  command: celery -A tasks beat --loglevel=info
  environment:
    - CELERY_BROKER_URL=redis://celery-redis:6379/0
  depends_on:
    - celery-redis
  volumes:
    - ./celery-worker:/app/celery-worker
```

### 3. Integrate Executor Pool Initialization
Add to `tasks.py` or create a startup script that runs automatically:
```python
# In tasks.py, after creating executor_pool
if not redis_client.exists("executors:available"):
    logger.info("Initializing executor pool...")
    executor_pool.initialize_pool(executor_urls)
```

### 4. Remove Legacy Code Path
In `tasks.py`, remove the legacy executor router fallback:
```python
# Remove this section (around line 209):
else:
    # Legacy path: find available executor (should not be reached with task chaining)
    logger.warning(f"evaluate_code called without executor_url for {eval_id} - using legacy path")
    executor_url = get_available_executor_url()
    # ...
```

## Future Improvements

### 1. Consolidate Task Management
The functionality in `task_management.py` could be useful but overlaps with `api/celery_client.py`. Consider:
- Moving useful functions to a shared module
- Or removing it entirely if the API client covers all needs

### 2. DLQ API Endpoints
The Dead Letter Queue is implemented but has no API to view/manage failed tasks. Consider adding:
- `/api/dlq/list` - List failed tasks
- `/api/dlq/{task_id}` - Get details of a failed task
- `/api/dlq/{task_id}/retry` - Retry a failed task
- `/api/dlq/stats` - Get DLQ statistics

### 3. Monitoring and Maintenance
If implementing Celery Beat:
- Add monitoring for scheduled task execution
- Consider additional maintenance tasks:
  - Cleanup old DLQ entries
  - Archive completed evaluations
  - Health check for executor pool

## Benefits of Cleanup
- Reduced confusion about which code is active
- Smaller Docker image (fewer files to copy)
- Clearer architecture for new developers
- Easier to maintain and debug