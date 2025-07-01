# Queue Service (Legacy System)

A simple REST API for task queueing that provides network-accessible task distribution for the Crucible platform. Currently handles 50% of evaluation traffic as part of a gradual migration to Celery.

## Overview

The Queue Service acts as a lightweight task queue, serving as the legacy queueing system while the platform migrates to Celery. It manages the lifecycle of evaluation tasks from submission to completion using simple Python data structures.

**Current Status**: This service runs alongside Celery in a 50/50 traffic split configuration, allowing for A/B testing and gradual migration.

## Features

- **FIFO Task Queue**: First-in-first-out task processing
- **Task Registry**: Tracks all tasks and their current status
- **Position Tracking**: Shows queue position for pending tasks
- **Redis Events**: Publishes task events for monitoring
- **Health Monitoring**: Provides queue status and health checks
- **API Security**: Optional API key authentication
- **OpenAPI Documentation**: Auto-generated API documentation

## API Endpoints

### Core Endpoints
- `POST /tasks` - Enqueue a new evaluation task
- `GET /tasks/next` - Get the next task for processing (worker endpoint)
- `GET /tasks/{eval_id}` - Get status of a specific task
- `POST /tasks/{eval_id}/complete` - Mark task as completed
- `POST /tasks/{eval_id}/fail` - Mark task as failed

### Monitoring Endpoints
- `GET /health` - Health check with queue statistics
- `GET /status` - Overall queue status and metrics
- `DELETE /tasks` - Clear all tasks (admin endpoint)

### Documentation
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)
- `GET /openapi.json` - OpenAPI specification (JSON)
- `GET /openapi.yaml` - OpenAPI specification (YAML)

## Configuration

Environment variables:
- `REDIS_URL` - Redis connection URL (default: `redis://redis:6379`)
- `API_KEY` - Optional API key for authentication
- `PORT` - Service port (default: 8081)

## Migration Context

This service is part of a dual-queue architecture during the Celery migration:

```
API Gateway (50/50 split)
    ├─→ Queue Service (50%) → Queue Worker → executor-1
    └─→ Celery (50%) → Celery Workers → executor-2, executor-3
```

### Traffic Distribution
- **Current**: 50% of evaluations routed here
- **Target**: 0% (full migration to Celery)
- **Rollback**: Can handle 100% if Celery issues arise

### Why Keep Both Systems?
1. **Risk Mitigation**: Gradual migration reduces risk
2. **A/B Testing**: Compare performance between systems
3. **Rollback Capability**: Quick reversion if needed
4. **Zero Downtime**: No service interruption during migration

## Architecture

The service uses:
- **FastAPI** for the REST API framework
- **Redis** for event publishing (optional)
- **In-memory queue** using Python's deque for FIFO behavior
- **Task registry** as a dictionary for O(1) lookups

## Task Lifecycle

1. **Queued**: Task is submitted and waiting for processing
2. **Processing**: Task has been picked up by a worker
3. **Completed/Failed**: Task execution finished

## Integration

The Queue Service integrates with:
- **API Gateway**: Receives task submissions
- **Queue Workers**: Pull tasks for execution
- **Storage Service**: Workers update evaluation results
- **Monitoring**: Publishes events to Redis

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py

# Or with uvicorn
uvicorn app:app --reload --port 8081
```

## Docker

```bash
# Build image
docker build -t crucible-queue-service .

# Run container
docker run -p 8081:8081 crucible-queue-service
```

## Security Considerations

- Tasks contain code to be executed - treat as untrusted
- API key authentication available for production
- No persistent storage - tasks lost on restart
- Network policies should restrict access to workers only

## Limitations

- **No Persistence**: Tasks are stored in memory only
- **Single Instance**: No clustering support
- **Basic Priority**: Only FIFO ordering, no priority queues
- **No Retries**: Failed tasks are not automatically retried

## Future (Post-Migration)

Once Celery migration is complete (CELERY_PERCENTAGE=1.0), this service will be:
1. Kept in standby mode for emergency fallback
2. Eventually decommissioned after stability period
3. Code archived for reference

The Celery system provides all the missing features:
- Persistence via Redis
- Priority queue support (implemented)
- Retry logic with exponential backoff (implemented)
- Task TTL and Dead Letter Queue (implemented)
- Scheduled tasks via Celery Beat (future)