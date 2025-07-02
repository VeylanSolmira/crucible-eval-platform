# Event Bus Architecture for Microservices

## Current State (Monolithic app.py)

### Event Flow
1. **EVALUATION_QUEUED** 
   - Emitted by: QueuedEvaluationPlatform when evaluation submitted
   - Consumed by: handle_evaluation_queued() → stores in database

2. **EVALUATION_COMPLETED**
   - Emitted by: QueuedEvaluationPlatform when evaluation finishes
   - Consumed by: handle_evaluation_completed() → updates database with results

3. **SECURITY_VIOLATION**
   - Emitted by: Security scanner
   - Consumed by: handle_security_violation() → logs alert

## Current Microservices Implementation

### What We Have Now
- API Gateway writes directly to PostgreSQL via FlexibleStorageManager
- Queue service manages task state but doesn't persist
- Queue worker forwards results back to queue service
- **Gap**: Completed evaluation results aren't being stored!

### Event Flow Gaps
1. When queue-worker completes an evaluation, it posts to `/tasks/{eval_id}/complete`
2. Queue service updates its internal state
3. **Missing**: Nobody updates the database with the results

## Architecture Options

### Option 1: API Gateway Handles Storage (Current)
```
Frontend → API Gateway → Queue Service
              ↓
         PostgreSQL
```

**Pros:**
- Simple, works now
- Similar to Kubernetes (API server manages etcd)
- Single source of truth for storage

**Cons:**
- Not truly event-driven
- API Gateway has multiple responsibilities

**Implementation needed:**
- Queue service needs webhook to notify API Gateway of completions
- OR: API Gateway polls queue service for completed tasks

### Option 2: Redis Pub/Sub
```
Frontend → API Gateway → Queue Service
              ↓              ↓
           Redis ← Queue Worker
              ↓
     Storage Worker → PostgreSQL
```

**Pros:**
- True event-driven architecture
- Lightweight, already need Redis for Celery
- Real-time updates

**Cons:**
- Another service to manage
- Events aren't persistent (fire-and-forget)

### Option 3: Message Queue (RabbitMQ/Kafka)
```
Frontend → API Gateway → Queue Service
              ↓              ↓
         RabbitMQ ← Queue Worker
              ↓
     Storage Worker → PostgreSQL
```

**Pros:**
- Persistent messages
- Reliable delivery
- Can replay events
- Industry standard

**Cons:**
- More complex
- Another service to manage
- Overkill for current scale

### Option 4: Storage Service
```
Frontend → API Gateway → Queue Service
              ↓              ↓
      Storage Service   Queue Worker
              ↓              ↓
         PostgreSQL    Storage Service
```

**Pros:**
- True microservices pattern
- Storage logic isolated
- Can switch backends easily

**Cons:**
- Most complex option
- More network calls
- Coordination challenges

## Recommendation for Now

Actually, **Option 2 (Redis Pub/Sub)** better matches Kubernetes patterns!

### How Kubernetes Really Works
Kubernetes is inherently event-driven:
- API Server writes to etcd and publishes watch events
- Controllers subscribe to watch events and react
- Multiple controllers can watch the same resources
- Loosely coupled via event streams, not direct calls

### Corrected Analogy
```
Kubernetes:
API Server → etcd → watch events → Controllers → update status → watch events

Our Platform:
API Gateway → PostgreSQL → Redis events → Workers → update status → Redis events
```

### Why Redis Pub/Sub is the Right Choice
1. **Kubernetes-like**: Matches the watch/event pattern
2. **Loosely coupled**: Services communicate via events, not direct calls
3. **Scalable**: Multiple workers can subscribe to same events
4. **Resilient**: If a worker dies, events can be replayed
5. **Already needed**: We'll add Redis for Celery anyway

### Implementation Approach
1. Add Redis container to docker-compose
2. API Gateway publishes EVALUATION_QUEUED after storing
3. Queue worker subscribes to EVALUATION_QUEUED events
4. Queue worker publishes EVALUATION_COMPLETED when done
5. Storage worker subscribes to EVALUATION_COMPLETED and updates DB

## Future Migration Path

When we need true events (for scaling, multiple consumers, etc.):

1. **Phase 1**: Add Redis, API Gateway publishes events after storing
2. **Phase 2**: Add storage worker that consumes events
3. **Phase 3**: Remove storage logic from API Gateway
4. **Phase 4**: Consider RabbitMQ/Kafka if needed

## Implementation TODOs

### Immediate (Fix the Gap)
- [ ] Add `/internal/evaluation-completed` endpoint to API Gateway
- [ ] Update queue-worker to call this endpoint
- [ ] Add authentication between internal services

### Future (True Events)
- [ ] Add Redis container to docker-compose
- [ ] Implement pub/sub in API Gateway
- [ ] Create storage-worker service
- [ ] Add event replay capability