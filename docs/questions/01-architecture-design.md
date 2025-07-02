# Architecture & Design Questions

## 🟢 Basic Level

### Q1: Why did you choose a microservices architecture over a monolithic approach?

**Answer**: 
The microservices architecture was chosen for several key reasons:
1. **Independent scaling** - The executor service (CPU-intensive) can scale differently from the API service (I/O-bound)
2. **Security isolation** - Code execution is isolated in separate containers/services
3. **Technology flexibility** - Can use different languages/frameworks per service (though we stayed with Python)
4. **Team scalability** - Different teams could own different services in a larger organization

**Deep Dive**: 
The original platform was monolithic (`crucible-platform` container). The migration to microservices introduced:
- API Gateway pattern (`api-service`)
- Event-driven communication (Redis pub/sub)
- Service mesh concepts (internal API keys)
- Distributed storage layer

**Trade-offs acknowledged**:
- Increased complexity (network calls, service discovery)
- Distributed system challenges (eventual consistency, partial failures)
- More infrastructure overhead (multiple containers)

**Follow-up questions**:
- How do you handle distributed transactions?
- What happens when one service fails?
- How do you maintain data consistency?

---

### Q2: Explain the event-driven architecture using Redis. Why Redis over RabbitMQ or Kafka?

**Answer**:
Redis was chosen as our event bus for:
1. **Simplicity** - Redis pub/sub is straightforward, no complex setup
2. **Dual purpose** - Also serves as cache and Celery broker
3. **Low latency** - In-memory operations, perfect for our use case
4. **Sufficient durability** - Redis persistence meets our needs

**Deep Dive**:
Our event flow:
```
User submits code -> API publishes event -> Storage Worker subscribes -> Database write
                  -> Queue Worker subscribes -> Triggers execution
```

Redis configuration shows our priorities:
```
--appendonly yes          # Durability
--maxmemory-policy volatile-lru  # Cache eviction
--save "60 10000"        # Persistence strategy
```

**Why not alternatives**:
- **RabbitMQ**: Overkill for our message volume, more complex setup
- **Kafka**: Built for high-throughput streaming, not our use case
- **AWS SQS**: Wanted to avoid cloud vendor lock-in

**Code Reference**: 
- Event publishing: `storage/event_publisher.py`
- Event consumption: `storage-worker/app.py:49-67`

---

## 🟡 Intermediate Level

### Q3: How do you handle service discovery and inter-service communication?

**Answer**:
We use Docker Compose's built-in DNS for service discovery:
1. **Service names as hostnames** - `http://storage-service:8082`
2. **Environment variables** for service URLs
3. **Health checks** ensure services are ready before communication
4. **Internal API keys** for service-to-service auth

**Deep Dive**:
No external service discovery (Consul, etcd) needed because:
- Docker Compose provides reliable DNS
- Service topology is relatively static
- Health checks prevent calls to unhealthy services

Communication patterns:
```python
# Synchronous HTTP (api/microservices_gateway.py:89)
async with httpx.AsyncClient() as client:
    response = await client.post(f"{STORAGE_SERVICE_URL}/evaluations/")

# Asynchronous events (storage/event_publisher.py:41)
self.redis_client.publish(channel, message)
```

**Security measures**:
- Internal network (`docker-api` network is internal)
- API keys for service authentication
- No external access to internal services

---

### Q4: Explain the storage layer abstraction. Why support multiple backends?

**Answer**:
The storage layer (`storage/base.py`) provides an abstract interface with multiple implementations:
1. **PostgreSQL** - Primary, ACID-compliant storage
2. **File system** - Fallback, useful for development
3. **Redis** - Caching layer

This abstraction enables:
- Easy testing with different backends
- Gradual migration between storage systems
- Disaster recovery (fallback options)
- Performance optimization (cache layer)

**Deep Dive**:
Abstract base class pattern:
```python
class StorageBackend(ABC):
    @abstractmethod
    async def save_evaluation(self, evaluation: EvaluationCreate) -> EvaluationResponse:
        pass
```

Factory pattern for backend selection:
```python
# storage/factory.py
def get_storage_backend(backend_type: str) -> StorageBackend:
    if backend_type == "database":
        return DatabaseBackend()
    elif backend_type == "file":
        return FileBackend()
```

**Real-world benefits**:
- Started with file storage for rapid prototyping
- Migrated to PostgreSQL without changing API
- Added Redis caching transparently

---

## 🔴 Advanced Level

### Q5: How does the system maintain consistency in a distributed environment?

**Answer**:
We use several patterns to maintain consistency:

1. **Event Sourcing Lite** - All state changes flow through events
2. **Idempotent Operations** - Evaluations have unique IDs, preventing duplicates
3. **Eventual Consistency** - Storage writes are async but ordered
4. **Saga Pattern** - For multi-step workflows (create → execute → store results)

**Deep Dive**:
Key design decisions:
- **No distributed transactions** - Accept eventual consistency
- **Event ordering** - Redis pub/sub maintains order per channel
- **Retries with backoff** - Handle transient failures
- **Dead letter queues** - Capture failed operations

Example flow:
```
1. API assigns UUID to evaluation (idempotency key)
2. Publishes creation event
3. Storage worker processes event (may retry)
4. Execution happens independently
5. Results event updates storage
6. Client polls for eventual result
```

Consistency boundaries:
- **Strong consistency**: Within single service (PostgreSQL transactions)
- **Eventual consistency**: Across services (event-driven updates)
- **Causal consistency**: Event ordering preserves causality

**Code references**:
- Idempotent evaluation creation: `api/microservices_gateway.py:121`
- Event ordering: `storage-worker/app.py:subscribe_to_events()`
- Retry logic: `celery-worker/tasks.py:@celery_app.task(bind=True, max_retries=3)`

---

### Q6: Describe the Celery migration strategy. How do you achieve zero-downtime migration?

**Answer**:
The migration from custom queue to Celery uses a **gradual rollout** strategy:

1. **Dual-write period** - Both systems handle traffic
2. **Percentage-based routing** - Start with 10%, increase gradually
3. **Feature flags** - `CELERY_ENABLED` and `CELERY_PERCENTAGE`
4. **Separate infrastructure** - Celery uses different Redis instance
5. **Rollback capability** - Can instantly revert to 0% Celery

**Deep Dive**:
Implementation in `api/microservices_gateway.py:142-150`:
```python
if CELERY_ENABLED and random.random() < CELERY_PERCENTAGE:
    # Route to Celery
    task = celery_app.send_task('tasks.evaluate_code', ...)
else:
    # Route to legacy queue
    await queue_client.submit_evaluation(...)
```

Monitoring during migration:
- Flower dashboard for Celery metrics
- Comparison script to verify both systems produce same results
- Gradual percentage increase: 10% → 25% → 50% → 90% → 100%

**Why this approach**:
- No "big bang" migration risk
- Can monitor error rates at each stage
- Easy rollback at any point
- Validates Celery under real load

**Timeline**:
1. Week 1-2: Dual systems, 10% traffic
2. Week 3-4: Increase to 50% 
3. Week 5-6: Move to 90%
4. Week 7-8: Full migration, decommission legacy

---

## 🟣 METR-Specific

### Q7: How does the architecture support AI safety evaluation requirements?

**Answer**:
The architecture addresses key AI safety evaluation needs:

1. **Complete Isolation** - Each evaluation runs in a fresh container
2. **Resource Controls** - CPU, memory, time limits enforced
3. **Audit Trail** - Every execution logged with inputs/outputs
4. **Network Isolation** - No internet access from execution environment
5. **Reproducibility** - Deterministic environment per evaluation

**Deep Dive**:
Security layers:
```
User Code -> Docker Container -> gVisor/runsc (future) -> Resource Limits -> Network Policies
```

Monitoring for suspicious behavior:
- Execution time tracking
- Resource usage monitoring
- System call filtering (planned)
- File system access controls

**Specific safeguards**:
```python
# executor_service/docker_executor.py
container = docker_client.containers.run(
    "python:3.11-slim",
    mem_limit="256m",
    cpu_quota=50000,  # 0.5 CPU
    network_mode="none",  # No network
    read_only=True,      # Read-only root
)
```

**Future enhancements**:
- gVisor for system call filtering
- Behavioral analysis of code patterns
- GPU isolation for ML workloads
- Enhanced audit logs for compliance

---

## Key Points Summary

1. **Microservices** chosen for isolation, scaling, and security
2. **Event-driven** architecture with Redis for loose coupling
3. **Storage abstraction** enables flexibility and testing
4. **Consistency** through event sourcing and idempotency
5. **Zero-downtime migration** via gradual rollout
6. **AI safety** through defense-in-depth isolation

## Hands-On Exercises

1. **Trace an evaluation**: Follow a code submission from API to result storage
2. **Modify routing**: Change Celery percentage and observe traffic split
3. **Add a service**: Create a new microservice and integrate it
4. **Break something**: Stop a service and observe system resilience
5. **Performance test**: Submit 100 concurrent evaluations and analyze bottlenecks