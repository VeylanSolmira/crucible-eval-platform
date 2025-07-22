# Storage Worker

Event-driven worker service that subscribes to Redis events and persists evaluation data to storage.

## Overview

The Storage Worker follows the Kubernetes controller pattern - it watches for specific events and takes action based on them. This service is responsible for all database writes, ensuring data consistency and providing a single point of truth for evaluation state.

## Architecture Pattern

```
┌─────────────┐      Redis PubSub       ┌──────────────┐
│   Services  │─────────Events─────────▶│Storage Worker│
└─────────────┘                         └──────┬───────┘
                                               │
                                               ▼
                                        ┌──────────────┐
                                        │   Storage    │
                                        │  (DB/File)   │
                                        └──────────────┘
```

## Features

- **Event-Driven**: Subscribes to Redis pub/sub channels
- **Flexible Storage**: Supports multiple storage backends via FlexibleStorageManager
- **Structured Logging**: Uses structlog for JSON-formatted logs
- **Health Monitoring**: FastAPI endpoint for health checks
- **Graceful Shutdown**: Properly closes connections on termination
- **Event Confirmation**: Publishes storage confirmation events

## Event Subscriptions

The worker subscribes to these Redis channels:
- `evaluation:queued` - New evaluation submitted
- `evaluation:completed` - Evaluation finished successfully
- `evaluation:failed` - Evaluation failed or timed out

## Event Publishing

After processing, the worker publishes to:
- `storage:evaluation:created` - Confirms new evaluation stored
- `storage:evaluation:updated` - Confirms evaluation update stored

## Storage Operations

### On `evaluation:queued`
- Creates new evaluation record
- Sets status to 'queued'
- Stores code and metadata
- Publishes confirmation event

### On `evaluation:completed`
- Updates evaluation status to 'completed'
- Stores output and results
- Updates success flag
- Publishes confirmation event

### On `evaluation:failed`
- Updates evaluation status to 'failed'
- Stores error message
- Sets success to false
- Publishes confirmation event

## Configuration

Environment variables:
- `REDIS_URL` - Redis connection URL (default: `redis://redis:6379`)
- `DATABASE_URL` - PostgreSQL connection string
- `FILE_STORAGE_PATH` - Path for file-based storage
- `STORAGE_BACKEND` - Primary storage backend (database/file/memory)
- `ENABLE_CACHING` - Enable in-memory caching

## Health Check

The worker provides a health endpoint at port 8085:
- `GET /health` - Returns worker and subsystem health status

Health response includes:
- Redis connectivity
- Storage backend health
- Events processed count
- Overall health status

## Structured Logging

All logs are JSON-formatted for easy parsing:
```json
{
  "event": "storage_worker.initialized",
  "backend": "flexible_storage",
  "redis_url": "redis://redis:6379",
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
docker build -t crucible-storage-worker .

# Run container
docker run crucible-storage-worker
```

## Integration

The Storage Worker integrates with:
- **API Service**: Listens for evaluation events
- **Queue Worker**: Listens for completion events
- **Storage Service**: Could be replaced by REST calls to storage-service
- **Redis**: Event bus for all services

## Monitoring

Key metrics to monitor:
- Event processing rate
- Storage write failures
- Redis connection stability
- Event processing lag
- Memory usage (if caching enabled)

## Design Decisions

### Why Event-Driven?
- **Decoupling**: Services don't need to know about storage
- **Scalability**: Can run multiple workers for high load
- **Reliability**: Events can be replayed if needed
- **Flexibility**: Easy to add new event handlers

### Why Separate Worker?
- **Single Responsibility**: Only this service writes to storage
- **Consistency**: Prevents race conditions
- **Monitoring**: Easy to track all storage operations
- **Migration**: Can change storage without touching other services

## Error Handling

- **Invalid JSON**: Logs error and continues processing
- **Missing Fields**: Validates required fields before storage
- **Storage Failures**: Logs detailed errors for debugging
- **Redis Disconnection**: Health check reports unhealthy

## Limitations

- **No Event Replay**: Lost events aren't recovered
- **No Deduplication**: Duplicate events create duplicate records
- **Memory Usage**: FastAPI adds ~20-30MB overhead for health endpoint

## Future Improvements

- Event replay mechanism for reliability
- Deduplication using event IDs
- Batch processing for efficiency
- Dead letter queue for failed events
- Prometheus metrics endpoint
- Replace FastAPI health endpoint with lighter alternative