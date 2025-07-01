# Celery Integration Architecture Notes

## Current Architecture vs Celery Architecture

### Current Queue-Worker Architecture
```
API → Queue Service (deque) → Queue Worker → Creates Isolated Container → Execution
```

- Queue Worker creates fresh Docker containers for each execution
- Complete isolation between executions
- No persistent executor services needed

### Celery Architecture (As Configured)
```
API → Celery (Redis) → Celery Worker → Executor Service → Execution
```

- Celery Worker calls existing executor services
- Executor services are long-running containers
- Less isolation but faster execution

## Service Port Mappings

### Current Services
- **API Service**: 8080 (internal)
- **Queue Service**: 8081 (internal)
- **Storage Service**: 8082 (exposed)
- **Executor Service**: 8083 (internal)
- **Storage Worker**: 8085 (health check)

### Celery Services
- **Celery Redis**: 6380 (exposed, separate from event Redis)
- **Flower Dashboard**: 5555 (exposed)
- **Event Redis**: 6379 (exposed, for inter-service communication)

## Docker Compose Overlays

1. **docker-compose.yml** - Base services
2. **docker-compose.dev.yml** - Frontend hot reload for development
3. **docker-compose.celery.yml** - Celery services overlay

### Using Celery Overlay
```bash
# Start all services including Celery
docker-compose -f docker-compose.yml -f docker-compose.celery.yml up -d

# Start with frontend hot reload AND Celery
docker-compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.celery.yml up -d
```

## Key Architectural Decisions

### Two Redis Instances
1. **Event Redis (6379)**: Inter-service pub/sub communication
   - Optimized for volatile messages
   - Moderate persistence for event recovery
   
2. **Celery Redis (6380)**: Task queue management
   - Optimized for queue operations
   - Strong persistence for task durability

### Executor Service Integration
The Celery worker is configured to use executor services directly rather than creating isolated containers. This means:

**Pros:**
- Faster execution (no container startup overhead)
- Simpler Celery worker implementation
- Can leverage executor service features

**Cons:**
- Less isolation between executions
- Requires careful resource management
- Security considerations for shared executor

### Future Considerations

1. **Isolated Container Execution in Celery**
   - Modify Celery worker to create containers like queue-worker does
   - Better security and isolation
   - Higher latency per execution

2. **Hybrid Approach**
   - Use executor services for trusted code
   - Create isolated containers for untrusted code
   - Route based on task metadata

3. **Multi-Executor Load Balancing**
   - Configure Celery to use executor-1, executor-2, etc.
   - Round-robin or least-loaded selection
   - Health check integration