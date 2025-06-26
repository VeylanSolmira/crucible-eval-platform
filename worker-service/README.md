# Worker Service

Task processing worker that pulls evaluation tasks from the queue and executes them using available execution engines.

## Overview

The Worker Service is a pull-based worker that continuously polls the Queue Service for new tasks and executes them using the appropriate execution engine (Docker or gVisor). It reuses the existing execution infrastructure from the monolithic application while operating as an independent microservice.

## Architecture

```
┌──────────────┐  pull task   ┌──────────────┐
│Queue Service │◀─────────────│Worker Service│
└──────────────┘              └──────┬───────┘
       ▲                             │
       │                             ▼
       │                      ┌──────────────┐
       └──────complete────────│  Execution   │
                              │   Engine     │
                              └──────────────┘
```

## Features

- **Pull-Based Processing**: Polls queue for available tasks
- **Multiple Execution Engines**: Supports Docker and gVisor
- **Automatic Fallback**: Falls back to Docker if requested engine unavailable
- **Structured Logging**: Detailed logging with context
- **Health Monitoring**: FastAPI endpoint for health checks
- **Error Recovery**: Exponential backoff on failures
- **Event Publishing**: Emits events for monitoring

## Execution Engines

### Docker Engine
- Default execution environment
- Runs code in isolated containers
- Available on all platforms

### gVisor Engine
- Enhanced security isolation
- Linux only
- Automatically detected and initialized

## Configuration

Environment variables:
- `QUEUE_SERVICE_URL` - Queue service URL (default: `http://queue:8081`)
- `API_SERVICE_URL` - API service URL (default: `http://api:8080`)
- `API_KEY` - Optional API key for queue authentication
- `HOSTNAME` - Worker identifier (default: `worker-1`)

## Task Processing Flow

1. **Poll Queue**: GET request to `/tasks/next`
2. **Execute Task**: Run code using appropriate engine
3. **Report Result**: POST to `/tasks/{eval_id}/complete` or `/fail`
4. **Emit Event**: Publish completion/failure event
5. **Repeat**: Continue polling for next task

## Error Handling

### Connection Failures
- Exponential backoff (5s, 10s, 15s... max 30s)
- Logs detailed error information
- Continues retrying indefinitely

### Execution Failures
- Reports failure to queue service
- Emits failure event
- Continues processing next task

### Engine Fallback
- If requested engine unavailable, falls back to Docker
- Logs warning about fallback
- Ensures task is still processed

## Health Check

The worker provides a health endpoint at port 8082:
- `GET /health` - Returns worker status and configuration

Health response includes:
- Worker ID
- Available execution engines
- Queue service URL
- Overall health status

## Structured Logging

All logs include contextual information:
```
{
  "event": "processing_task_started",
  "eval_id": "abc123",
  "engine": "docker",
  "worker": "worker-1",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the worker
python app.py
```

## Docker

```bash
# Build image
docker build -t crucible-worker-service .

# Run container (needs Docker socket)
docker run -v /var/run/docker.sock:/var/run/docker.sock \
  crucible-worker-service
```

## Integration

The Worker Service integrates with:
- **Queue Service**: Pulls tasks and reports results
- **Execution Engines**: Uses existing Docker/gVisor infrastructure
- **Event Bus**: Publishes task completion events
- **Storage Worker**: Listens to completion events

## Scaling

### Horizontal Scaling
- Run multiple worker instances
- Each worker has unique ID
- Queue service handles distribution

### Resource Management
- Each worker processes one task at a time
- Resource limits applied per container
- Workers are stateless

## Monitoring

Key metrics to monitor:
- Task processing rate
- Execution success/failure ratio
- Queue polling frequency
- Engine availability
- Connection errors

## Security Considerations

- Workers should run with minimal privileges
- Docker socket access required for container creation
- Network policies should restrict external access
- API key authentication for queue access

## Design Decisions

### Why Pull-Based?
- **Simplicity**: No complex push mechanisms
- **Reliability**: Workers control their load
- **Flexibility**: Easy to add/remove workers

### Why Reuse Engines?
- **Proven Code**: Existing engines are tested
- **Consistency**: Same execution behavior
- **Maintenance**: Single codebase for engines

## Limitations

- **Single Task**: Processes one task at a time
- **No Priorities**: FIFO processing only
- **No Caching**: Doesn't cache execution results
- **Platform Specific**: gVisor only on Linux

## Future Improvements

- Concurrent task processing
- Task type specialization
- Result caching for duplicate code
- Metrics endpoint for Prometheus
- WebSocket connection to queue for real-time updates
- Support for more execution engines (Firecracker, etc.)