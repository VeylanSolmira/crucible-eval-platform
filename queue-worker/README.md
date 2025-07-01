# Queue Worker (Legacy System)

Scheduler service that pulls tasks from the legacy queue and routes them to executor-1. Currently processes 50% of platform traffic while Celery handles the other 50%.

## Overview

The Queue Worker acts as a task scheduler for the legacy queue system. It continuously pulls tasks from the Queue Service and routes them exclusively to executor-1, while Celery workers handle the other 50% of traffic using executor-2 and executor-3. This separation enables A/B testing during the migration to Celery.

## Architecture

Current dual-system architecture:

```
API Gateway (50/50 split)
    │
    ├─→ Queue Service (50%)
    │        │
    │        ▼
    │   Queue Worker ──────────→ Executor-1 (dedicated)
    │        │
    │        ▼
    │     Redis (events)
    │
    └─→ Celery (50%)
             │
             ▼
        Celery Workers ────┬───→ Executor-2
                          └───→ Executor-3
```

## Features

- **Task Routing**: Distributes tasks to available executors
- **Health Monitoring**: Checks executor health before routing
- **Load Balancing**: Random distribution with health checks
- **Event Publishing**: Publishes completion/failure events
- **Auto-Discovery**: Discovers executor instances
- **Error Recovery**: Exponential backoff on failures
- **Status Tracking**: Tracks routing metrics
- **OpenAPI Documentation**: Auto-generated API documentation

## API Endpoints

### Monitoring
- `GET /health` - Service health with executor status
- `GET /status` - Detailed worker and executor status

### Documentation
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)
- `GET /openapi.json` - OpenAPI specification (JSON)
- `GET /openapi.yaml` - OpenAPI specification (YAML)

## Task Flow

1. **Pull Task**: GET request to queue service
2. **Select Executor**: Find healthy executor using round-robin
3. **Route Task**: POST task to selected executor
4. **Await Result**: Executor processes synchronously
5. **Report Result**: Update queue with completion/failure
6. **Publish Event**: Notify other services via Redis

## Migration Context

### Current State
- Processes tasks from Queue Service (50% of traffic)
- Routes exclusively to executor-1
- Runs parallel to Celery workers processing the other 50%

### Why Dedicated Executor?
1. **Isolation**: Clean A/B testing between queue systems
2. **Performance Comparison**: Compare executor-1 vs executor-2/3
3. **Debugging**: Easier to trace issues to specific queue system
4. **Rollback**: Can scale executor-1 if Celery has issues

### Post-Migration Plan
Once Celery handles 100% traffic:
1. This worker enters standby mode
2. Executor-1 reserved for emergency fallback
3. Eventually decommissioned after stability period

## Configuration

Environment variables:
- `QUEUE_SERVICE_URL` - Queue service URL (default: `http://queue:8081`)
- `QUEUE_API_KEY` - Optional API key for queue access
- `REDIS_URL` - Redis connection URL (default: `redis://redis:6379`)
- `EXECUTOR_COUNT` - Number of executor instances (default: 1) # Limited to executor-1
- `EXECUTOR_BASE_URL` - Base URL for executors (default: `http://executor`)
- `HOSTNAME` - Worker identifier (default: `queue-worker-1`)

## Executor Discovery

Current configuration:
- Only uses `executor-1` (EXECUTOR_COUNT=1)
- URL: `http://executor-1:8083`
- No round-robin needed with single executor

Note: executor-2 and executor-3 are reserved for Celery workers

## Health Checking

Before routing each task:
1. Sends GET request to `/health` endpoint
2. 2-second timeout for health checks
3. Marks executor as unhealthy on failure
4. Routes to next healthy executor

## Event Publishing

Published events:
- `evaluation:completed` - Task completed successfully
- `evaluation:failed` - Task failed or timed out

Event format:
```json
{
  "eval_id": "abc123",
  "result": {
    "status": "completed",
    "output": "...",
    "exit_code": 0
  }
}
```

## Load Balancing

Current strategy:
- Random selection with health checking
- No persistent state between tasks
- Simple but effective for even distribution

Future enhancements:
- Track executor load/performance
- Weighted routing based on capacity
- Sticky sessions for related tasks
- Priority-based scheduling

## Error Handling

### No Healthy Executors
- Marks task as failed
- Reports error to queue service
- Logs detailed error information

### Executor Errors
- Captures HTTP error responses
- Reports failure to queue
- Continues processing other tasks

### Connection Failures
- Exponential backoff (5s, 10s, 15s... max 30s)
- Continues retrying indefinitely
- Tracks consecutive errors

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py

# Or with uvicorn
uvicorn app:app --reload --port 8084
```

## Docker

```bash
# Build image
docker build -t crucible-queue-worker .

# Run container
docker run -p 8084:8084 crucible-queue-worker
```

## Integration

The Queue Worker integrates with:
- **Queue Service**: Pulls tasks and reports results
- **Executor Services**: Routes tasks for execution
- **Redis**: Publishes task events
- **Storage Worker**: Consumes published events

## Monitoring

Key metrics to monitor:
- Tasks routed per minute
- Executor health status
- Failed routing attempts
- Queue polling frequency
- Event publishing success rate

## Design Decisions

### Why Separate Scheduler?
- **Scalability**: Scale scheduling independently
- **Intelligence**: Add routing logic without touching executors
- **Monitoring**: Central point for task metrics
- **Evolution**: Easy path to Celery/Kubernetes jobs

### Why Health Checks?
- **Reliability**: Avoid sending tasks to dead executors
- **Fast Failure**: Detect issues quickly
- **Auto-Recovery**: Executors rejoin when healthy

## Limitations

- **Single Queue**: Pulls from one queue only
- **No Persistence**: Routing decisions not saved
- **Basic Strategy**: Random selection only
- **No Retries**: Failed tasks not retried

## Migration Status

### Current Phase: 50/50 Split
- This worker handles 50% of evaluation traffic
- Celery handles the other 50% with superior features
- Performance metrics being compared

### Next Phase: Gradual Reduction
- CELERY_PERCENTAGE will increase to 0.9 (90%)
- This worker handles only 10% as safety net
- Monitor for any degradation

### Final Phase: Standby Mode
- CELERY_PERCENTAGE = 1.0 (100% to Celery)
- This worker remains idle but ready
- Can be reactivated via FORCE_LEGACY_QUEUE=true

### Decommission Timeline
- 30 days after 100% Celery traffic
- Archive code and documentation
- Remove containers and services