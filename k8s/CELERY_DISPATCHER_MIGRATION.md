# Celery to Dispatcher Migration Guide

## Overview

This guide explains how to update the Celery worker to use the new dispatcher service instead of directly managing executors.

## What Changes in Celery Worker

### Before (Direct Executor Management)
```python
# tasks.py
executor_pool = ExecutorPool(redis_client)
executor_url = executor_pool.claim_executor(eval_id)
response = httpx.post(f"{executor_url}/execute", json={...})
```

### After (Dispatcher Service)
```python
# tasks.py
DISPATCHER_URL = os.environ.get("DISPATCHER_SERVICE_URL", "http://dispatcher-service:8090")

response = httpx.post(f"{DISPATCHER_URL}/execute", json={
    "eval_id": eval_id,
    "code": code,
    "timeout": timeout,
    "memory_limit": "512Mi",
    "cpu_limit": "500m"
})
```

## Key Differences

1. **No Executor Pool Management**
   - Remove all executor pool logic
   - No claiming/releasing executors
   - No Redis-based pool tracking

2. **Single Endpoint**
   - All requests go to dispatcher service
   - Dispatcher handles K8s Job creation
   - No routing logic needed

3. **Simplified Error Handling**
   - Just handle HTTP errors from dispatcher
   - No need to handle executor availability

## Environment Variables

Remove these from Celery:
- `EXECUTOR_COUNT`
- `EXECUTOR_BASE_URL` 
- `EXECUTOR_START_INDEX`

Add this:
- `DISPATCHER_SERVICE_URL=http://dispatcher-service:8090`

## Example Celery Task Update

```python
@app.task(bind=True, max_retries=3)
def run_evaluation(self, eval_id: str, code: str, language: str = "python"):
    """Execute code evaluation using dispatcher service."""
    
    try:
        # Call dispatcher to create K8s Job
        response = httpx.post(
            f"{DISPATCHER_URL}/execute",
            json={
                "eval_id": eval_id,
                "code": code,
                "language": language,
                "timeout": 300,
                "memory_limit": "512Mi",
                "cpu_limit": "500m"
            },
            timeout=30.0
        )
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"Created job {result['job_name']} for eval {eval_id}")
        
        # Store job name for tracking
        redis_client.set(f"eval:{eval_id}:job", result['job_name'], ex=3600)
        
        # Monitor job status (optional - could be separate task)
        monitor_job_status.delay(eval_id, result['job_name'])
        
    except httpx.HTTPError as e:
        logger.error(f"Failed to create job for {eval_id}: {e}")
        raise self.retry(exc=e, countdown=60)

@app.task
def monitor_job_status(eval_id: str, job_name: str):
    """Monitor K8s Job status."""
    
    try:
        response = httpx.get(f"{DISPATCHER_URL}/status/{job_name}")
        response.raise_for_status()
        
        status = response.json()
        
        if status['status'] == 'succeeded':
            # Get logs and mark as complete
            logs_response = httpx.get(f"{DISPATCHER_URL}/logs/{job_name}")
            logs = logs_response.json().get('logs', '')
            
            # Publish completion event
            publish_evaluation_completed(eval_id, success=True, output=logs)
            
        elif status['status'] == 'failed':
            # Mark as failed
            publish_evaluation_completed(eval_id, success=False, error="Job failed")
            
        elif status['status'] == 'running':
            # Check again in 10 seconds
            monitor_job_status.apply_async(args=[eval_id, job_name], countdown=10)
            
    except Exception as e:
        logger.error(f"Error monitoring job {job_name}: {e}")
```

## Benefits of This Approach

1. **Simpler Celery Worker**
   - No executor management complexity
   - Focus on queue processing only

2. **Better Scalability**
   - K8s handles all scheduling
   - No executor bottlenecks

3. **Improved Observability**
   - All evaluations visible as K8s Jobs
   - Native K8s monitoring tools work

4. **Easier Testing**
   - Mock single HTTP endpoint
   - No complex pool state to manage

## Rollback Plan

If needed, you can rollback by:
1. Deploying executor services again
2. Setting `EXECUTOR_BASE_URL` in Celery
3. Re-enabling executor pool initialization

The dispatcher service can coexist with executors during migration.