# Event-Driven Architecture Flow

## Complete Microservices Architecture with Storage Worker

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Frontend  │────▶│ API Gateway  │────▶│    Queue    │
└─────────────┘     └──────┬───────┘     └──────┬──────┘
                           │                      │
                           ▼                      ▼
                    ┌─────────────┐        ┌─────────────┐
                    │    Redis    │        │Queue Worker │
                    │  Pub/Sub    │        └──────┬──────┘
                    └──────┬──────┘               │
                           │                      ▼
                           ▼                ┌─────────────┐
                    ┌─────────────┐         │  Executor   │
                    │   Storage   │         │  Service    │
                    │   Worker    │         └──────┬──────┘
                    └──────┬──────┘               │
                           │                      ▼
                           ▼                ┌─────────────┐
                    ┌─────────────┐         │Docker Proxy │
                    │ PostgreSQL  │         └─────────────┘
                    └─────────────┘
```

## Event Flow Details

### 1. Evaluation Submission
```
User submits code
    ↓
Frontend POST /api/eval
    ↓
API Gateway:
    - Generates eval_id
    - Publishes to Redis: "evaluation:queued" 
    - Forwards to Queue Service
    - Returns eval_id immediately (fast!)
    ↓
Queue Service:
    - Stores task in memory
    - Returns confirmation
```

### 2. Storage (Asynchronous)
```
Redis "evaluation:queued" event
    ↓
Storage Worker:
    - Receives event
    - Creates evaluation record in PostgreSQL
    - Publishes "storage:evaluation:created"
```

### 3. Execution
```
Queue Worker:
    - Polls Queue Service for tasks
    - Sends to Executor Service
    ↓
Executor Service:
    - Creates container via Docker Proxy
    - Runs code
    - Returns results
    ↓
Queue Worker:
    - Receives results
    - Updates Queue Service
    - Publishes to Redis: "evaluation:completed"
```

### 4. Result Storage (Asynchronous)
```
Redis "evaluation:completed" event
    ↓
Storage Worker:
    - Receives event with results
    - Updates PostgreSQL record
    - Publishes "storage:evaluation:updated"
```

### 5. Status Check
```
Frontend GET /api/eval-status/{eval_id}
    ↓
API Gateway:
    - Queries PostgreSQL directly
    - Returns current status
```

## Benefits of This Architecture

### 1. **Performance**
- API responds in milliseconds (no DB wait)
- Storage happens asynchronously
- Can batch database writes

### 2. **Scalability**
- Each service scales independently
- Multiple storage workers for high load
- Redis handles millions of messages/sec

### 3. **Resilience**
- If storage is slow, API still fast
- If storage worker dies, events queue in Redis
- Can replay events if needed

### 4. **Flexibility**
- Easy to add new event consumers
- Can transform data before storing
- Multiple storage destinations

### 5. **Observability**
- Clear event flow
- Each service has specific metrics
- Easy to trace evaluation lifecycle

## Redis Channels

### Published by API Gateway:
- `evaluation:queued` - New evaluation submitted

### Published by Queue Worker:
- `evaluation:started` - Execution began
- `evaluation:completed` - Execution succeeded
- `evaluation:failed` - Execution failed

### Published by Storage Worker:
- `storage:evaluation:created` - Stored in DB
- `storage:evaluation:updated` - Updated in DB

## Resource Usage (t2.micro optimized)

| Service | RAM | CPU | Purpose |
|---------|-----|-----|---------|
| API Gateway | 128MB | Low | Route requests, publish events |
| Queue Service | 100MB | Low | Manage task queue |
| Queue Worker | 128MB | Low | Route tasks to executors |
| Executor | 128MB | Medium | Create containers |
| Storage Worker | 128MB | Low | Write to database |
| Redis | 100MB | Low | Event bus |
| PostgreSQL | 200MB | Medium | Data persistence |
| Docker Proxy | 50MB | Low | Security boundary |
| **Total** | **~950MB** | | Fits in 1GB! |

## Deployment Commands

```bash
# Build all services
docker-compose build

# Start event-driven architecture
docker-compose up -d redis postgres
docker-compose up -d storage-worker
docker-compose up -d api-gateway queue queue-worker executor-1

# Watch events in real-time
docker exec -it crucible-redis redis-cli
> SUBSCRIBE evaluation:* storage:*

# Check storage worker logs
docker logs -f storage-worker

# Verify event flow
curl -X POST http://localhost:8080/api/eval \
  -H "Content-Type: application/json" \
  -d '{"code": "print(\"Hello, Events!\")"}'
```

## Next Steps

1. Add metrics to each service (Prometheus)
2. Add distributed tracing (OpenTelemetry)
3. Implement event replay for disaster recovery
4. Add event schema validation
5. Consider Kafka for event persistence