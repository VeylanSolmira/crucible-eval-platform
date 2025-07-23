# Job Monitoring Architecture

## Overview

This document describes the job monitoring architecture for the Crucible Platform, particularly how we track the status of Kubernetes Jobs created for code evaluations.

## Current Implementation (Event-Based in Dispatcher)

As of the current implementation, we use an **event-based monitoring approach** integrated into the dispatcher service. This replaces the previous polling-based approach that had up to 10-second delays.

### Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Celery    │───▶│  Dispatcher  │───▶│   Kubernetes    │
│   Worker    │    │   Service    │    │      Jobs       │
└─────────────┘    └──────┬───────┘    └────────┬────────┘
                          │                      │
                          │ Watch Events         │
                          ▼                      │
                   ┌──────────────┐              │
                   │    Redis     │◀─────────────┘
                   │  Pub/Sub     │    Job Events
                   └──────────────┘
```

### Implementation Details

1. **Event Monitoring**: The dispatcher service runs a background task that watches Kubernetes Job events using the K8s watch API
2. **Immediate Updates**: When a job changes state (pending → running → completed/failed), events are published immediately to Redis
3. **Feature Flag**: Controlled by `ENABLE_EVENT_MONITORING` environment variable (default: true)
4. **Graceful Degradation**: If event monitoring is disabled, falls back to Celery polling

### Code Structure

```python
# dispatcher_service/app.py

# Background monitoring task
async def monitor_job_events(app: FastAPI):
    """Watches Kubernetes job events and publishes status updates."""
    # Runs for the lifetime of the dispatcher
    # Uses kubernetes watch API with 5-minute reconnection timeout
    
# Event processor
async def process_job_event(event: Dict, redis_client: ResilientRedisClient):
    """Processes individual job events and publishes to Redis channels."""
    # Publishes: evaluation:running, evaluation:completed, evaluation:failed, evaluation:cancelled
```

## Alternative Architectures Considered

### 1. Polling in Celery Worker (Previous Implementation)
**Pros:**
- Simple implementation
- Celery handles retries/reliability

**Cons:**
- 10-second polling delay (poor UX)
- Wastes resources polling unchanged jobs
- Mixes business logic with infrastructure concerns

### 2. Dedicated Monitoring Service (Future State)
**Pros:**
- Single responsibility principle
- Can monitor ALL jobs regardless of creator
- Survives dispatcher restarts
- Could handle other monitoring tasks

**Cons:**
- Another service to deploy/maintain
- Additional complexity

### 3. Webhook/Admission Controller
**Pros:**
- True event-driven
- No polling or watching needed

**Cons:**
- Complex Kubernetes configuration
- Requires cluster-admin permissions
- Harder to develop/test locally

## Trade-offs of Current Approach

### Advantages
1. **Immediate Updates**: Sub-second status updates vs 10-second polling
2. **Efficient**: Only processes actual state changes
3. **Integrated**: No additional services needed
4. **Simple Migration Path**: Code can be lifted to dedicated service later

### Disadvantages
1. **Dispatcher Coupling**: Dispatchers must remain running for job lifetime
2. **Scaling Limitations**: Can't scale down dispatchers while jobs are running
3. **Failure Recovery**: If dispatcher crashes, monitoring stops for its jobs
4. **Resource Usage**: Each dispatcher maintains a watch connection

## Migration Path to Dedicated Service

When ready to move to a dedicated monitoring service:

1. **Extract Code**: Move `monitor_job_events` and `process_job_event` to new service
2. **Update Watch Scope**: Remove label selector to watch ALL jobs
3. **Add HA**: Deploy multiple replicas with leader election
4. **Update Feature Flag**: Disable event monitoring in dispatcher
5. **Deploy Service**: Roll out monitoring service before disabling in dispatcher

## Configuration

### Environment Variables

- `ENABLE_EVENT_MONITORING`: Enable/disable event monitoring (default: "true")
- `KUBERNETES_NAMESPACE`: Namespace to watch for jobs (default: "crucible")
- `REDIS_URL`: Redis connection for publishing events

### Redis Channels

Events are published to these Redis channels:
- `evaluation:running`: Job started executing
- `evaluation:completed`: Job finished successfully
- `evaluation:failed`: Job failed or errored
- `evaluation:cancelled`: Job was deleted before completion

### Event Payload Structure

```json
{
  "eval_id": "eval-123",
  "executor_id": "eval-123-job-abc",
  "container_id": "eval-123-job-abc",
  "timeout": 300,
  "started_at": "2024-01-01T00:00:00Z",
  "output": "...",
  "error": "...",
  "exit_code": 0,
  "metadata": {
    "job_name": "eval-123-job-abc",
    "completed_at": "2024-01-01T00:01:00Z"
  }
}
```

## Monitoring and Debugging

### Logs to Watch

```bash
# Dispatcher logs for monitoring
kubectl logs -f deployment/dispatcher-service -n crucible | grep -E "(monitor|event|watch)"

# Check if events are being published
redis-cli -h redis SUBSCRIBE "evaluation:*"
```

### Common Issues

1. **Watch Timeout**: Watch reconnects every 5 minutes - this is normal
2. **Missing Events**: Check if job has correct labels (`app=evaluation`)
3. **Delayed Events**: Ensure `ENABLE_EVENT_MONITORING=true`
4. **Memory Growth**: Watch connections may accumulate - monitor dispatcher memory

## Future Improvements

1. **Dedicated Monitoring Service**: Extract to separate service for better reliability
2. **Metrics**: Add Prometheus metrics for monitoring performance
3. **Event Deduplication**: Prevent duplicate events during reconnections
4. **Batch Processing**: Process multiple events in single Redis publish
5. **Circuit Breaker**: Add circuit breaker for Redis publishing