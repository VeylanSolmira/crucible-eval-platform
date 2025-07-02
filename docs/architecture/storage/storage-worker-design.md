# Storage Worker Design

## What is the Storage Worker?

The storage worker is a dedicated microservice that:
- **Subscribes** to Redis pub/sub channels for evaluation events
- **Persists** evaluation data to PostgreSQL (or other backends)
- **Publishes** confirmation events for other services
- **Decouples** storage logic from business logic

## Architecture Pattern

This follows the **Kubernetes Controller Pattern**:

```
Kubernetes Controller:
- Watches for resource changes (via API server)
- Takes action based on desired state
- Updates resource status
- Other controllers can react to status changes

Our Storage Worker:
- Watches for evaluation events (via Redis)
- Takes action based on event type
- Updates evaluation status in DB
- Other services can react to storage events
```

## Benefits of Storage Worker

### 1. **Single Responsibility**
- ONLY handles storage operations
- Easy to understand, test, and maintain
- No mixing of business logic with persistence

### 2. **Scalability**
```yaml
# Can run multiple instances for high load
replicas: 3
```
- Each worker processes events independently
- Redis pub/sub broadcasts to all subscribers
- Database handles concurrent writes

### 3. **Resilience**
- If storage worker crashes, events queue in Redis
- Can replay events if needed
- No data loss during restarts
- Graceful degradation (API still works, just no persistence)

### 4. **Flexibility**
- Easy to add new storage backends
- Can transform data before storing
- Add data validation/enrichment
- Archive old evaluations to S3

### 5. **Observability**
- Clear metrics: events processed, storage latency
- Easy to monitor storage health separately
- Can add detailed logging without cluttering API

## Event Flow

```
1. API Gateway receives evaluation request
   ↓
2. API Gateway publishes "evaluation:queued" to Redis
   ↓
3. Storage Worker receives event and stores in PostgreSQL
   ↓
4. Storage Worker publishes "storage:evaluation:created"
   ↓
5. Other services can react (e.g., notifications, analytics)

Later...

6. Queue Worker completes evaluation
   ↓
7. Queue Worker publishes "evaluation:completed" to Redis
   ↓
8. Storage Worker updates PostgreSQL with results
   ↓
9. Storage Worker publishes "storage:evaluation:updated"
```

## Comparison to Direct Storage

### Direct Storage (API Gateway writes to DB)
```python
# In API Gateway
def evaluate(request):
    eval_id = generate_id()
    storage.create_evaluation(eval_id, request.code)  # Blocking
    queue.submit(eval_id, request.code)
    return {"eval_id": eval_id}
```

**Problems:**
- API latency includes database write time
- If DB is slow, API is slow
- Tight coupling between API and storage
- Hard to change storage backend

### Event-Driven Storage (Storage Worker)
```python
# In API Gateway
async def evaluate(request):
    eval_id = generate_id()
    await redis.publish("evaluation:queued", {
        "eval_id": eval_id,
        "code": request.code
    })  # Non-blocking, very fast
    return {"eval_id": eval_id}
```

**Benefits:**
- API returns immediately (milliseconds)
- Storage happens asynchronously
- Can batch writes for efficiency
- Easy to add multiple storage destinations

## Future Enhancements

### 1. Event Sourcing
Store all events, not just current state:
```python
# Store events
events_table:
- eval_123_queued: {"timestamp": "...", "code": "..."}
- eval_123_started: {"timestamp": "...", "worker": "..."}
- eval_123_completed: {"timestamp": "...", "output": "..."}

# Rebuild state by replaying events
```

### 2. Multi-Backend Storage
```python
async def handle_evaluation_completed(data):
    # Store in PostgreSQL for queries
    await store_in_postgres(data)
    
    # Archive to S3 for long-term storage
    if len(data['output']) > 1_000_000:
        s3_url = await upload_to_s3(data)
        data['output_url'] = s3_url
    
    # Send to analytics system
    await send_to_analytics(data)
```

### 3. Data Pipeline Integration
- Send events to Kafka for data lake
- Stream to BigQuery for analytics
- Feed ML models for anomaly detection

## Implementation Checklist

- [x] Create storage worker service
- [x] Add Redis subscription logic
- [x] Handle all evaluation events
- [x] Add health check endpoint
- [ ] Add Redis to docker-compose
- [ ] Update API Gateway to publish events
- [ ] Update Queue Worker to publish completion events
- [ ] Add metrics (Prometheus)
- [ ] Add distributed tracing (OpenTelemetry)
- [ ] Test fault tolerance
- [ ] Document operational procedures