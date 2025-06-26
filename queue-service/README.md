# Queue Service

A simple REST API for task queueing that provides network-accessible task distribution for the Crucible platform.

## Overview

The Queue Service acts as a lightweight task queue, similar to what Redis/Celery would provide but using simple Python data structures. It manages the lifecycle of evaluation tasks from submission to completion.

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

## Future Improvements

- Replace with Redis/RabbitMQ for persistence
- Add priority queue support
- Implement task retry logic
- Add task TTL and expiration
- Support for delayed/scheduled tasks