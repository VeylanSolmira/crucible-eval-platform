# Celery & Task Processing Questions

## 🟢 Basic Level

### Q1: Why did you choose Celery over maintaining the custom queue system?

**Answer**:
Celery provides battle-tested features that would take months to implement:
1. **Automatic retries** with exponential backoff
2. **Priority queues** for different task types
3. **Monitoring** via Flower dashboard
4. **Horizontal scaling** - just add more workers
5. **Dead letter queues** for failed tasks
6. **Task routing** based on properties

The custom queue worked but lacked these production features.

**Deep Dive**:
Custom queue limitations:
- No automatic retry logic
- Basic FIFO, no priorities  
- No built-in monitoring
- Manual scaling required
- Lost tasks on crashes

Celery advantages demonstrated:
```python
# celery-worker/tasks.py
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def evaluate_code(self, eval_id: str, code: str, language: str):
    try:
        result = execute_code(code)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
```

---

### Q2: Explain the 50/50 traffic split strategy during migration.

**Answer**:
The gradual migration uses percentage-based routing:

```python
# api/microservices_gateway.py:142
if CELERY_ENABLED and random.random() < CELERY_PERCENTAGE:
    # Route to Celery
    task = celery_app.send_task('tasks.evaluate_code', 
                               args=[eval_id, code, language])
else:
    # Route to legacy queue
    await queue_client.submit_evaluation(evaluation_data)
```

Benefits:
1. **Risk mitigation** - Problems affect only X% of traffic
2. **Performance comparison** - Real metrics on both systems
3. **Easy rollback** - Just set `CELERY_PERCENTAGE=0`
4. **Gradual load** - Celery infrastructure scales with demand

**Current Status**: 50% of traffic goes to each system

---

## 🟡 Intermediate Level

### Q3: How does Celery task routing work in your implementation?

**Answer**:
We use multiple queues for different task priorities and types:

```python
# celery-worker/celery_config.py
task_routes = {
    'tasks.evaluate_code': {'queue': 'evaluation'},
    'tasks.high_priority_eval': {'queue': 'high_priority'},
    'tasks.batch_evaluation': {'queue': 'batch'},
    'tasks.cleanup': {'queue': 'maintenance'}
}

# Queue configurations
task_queues = (
    Queue('high_priority', priority=10),
    Queue('evaluation', priority=5),
    Queue('batch', priority=3),
    Queue('maintenance', priority=1)
)
```

**Deep Dive**:
Worker specialization:
```bash
# High-priority worker (future)
celery -A tasks worker -Q high_priority --concurrency=4

# Batch processing worker  
celery -A tasks worker -Q batch --concurrency=1

# General evaluation workers
celery -A tasks worker -Q evaluation,high_priority --concurrency=2
```

This enables:
- Premium users get `high_priority` queue
- Bulk submissions use `batch` queue
- System maintenance doesn't block evaluations

---

### Q4: Describe the Celery monitoring and debugging setup.

**Answer**:
Comprehensive monitoring through multiple channels:

1. **Flower Dashboard** (`http://localhost:5555`)
   - Real-time task status
   - Worker health
   - Queue depths
   - Task execution times

2. **Redis Integration**:
```python
# Monitor queue depth
redis-cli llen celery:queue:evaluation

# Watch task events
redis-cli monitor | grep celery
```

3. **Structured Logging**:
```python
# celery-worker/tasks.py
logger.info("Task started", extra={
    "task_id": self.request.id,
    "eval_id": eval_id,
    "retry_count": self.request.retries
})
```

**Deep Dive - Flower Metrics**:
- Task success/failure rates
- Average execution time per task type
- Worker CPU/memory usage
- Queue backlogs and trends

**Debugging Commands**:
```bash
# Inspect active tasks
celery -A tasks inspect active

# Check reserved tasks
celery -A tasks inspect reserved

# Purge a queue
celery -A tasks purge -Q evaluation
```

---

## 🔴 Advanced Level

### Q5: How do you handle task failures and implement resilience?

**Answer**:
Multi-layer failure handling:

1. **Automatic Retries**:
```python
@celery_app.task(bind=True, max_retries=3)
def evaluate_code(self, eval_id, code, language):
    try:
        result = execute_code(code)
    except TemporaryError as exc:
        # Exponential backoff: 60s, 120s, 240s
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    except PermanentError as exc:
        # Don't retry, send to DLQ
        self.update_state(state='FAILURE', meta={'error': str(exc)})
        send_to_dlq(self.request, exc)
```

2. **Dead Letter Queue**:
```python
# celery-worker/tasks.py:dlq_handler
@celery_app.task
def process_dlq():
    """Process failed tasks for analysis"""
    failed_tasks = redis_client.lrange('celery:dlq', 0, -1)
    for task in failed_tasks:
        analyze_failure(task)
        alert_if_critical(task)
```

3. **Circuit Breaker** (planned):
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure = None
        self.is_open = False
```

**Deep Dive - Failure Scenarios**:
- **Executor unavailable**: Retry with different executor
- **Code timeout**: Mark as failed, no retry
- **Memory exceeded**: Analyze if malicious, maybe retry with limits
- **Network issues**: Exponential backoff retry
- **Database down**: Circuit breaker opens, queue backs up

---

### Q6: Explain the Celery infrastructure setup and scaling strategy.

**Answer**:
Production-ready Celery infrastructure:

1. **Separate Redis Instance**:
```yaml
# docker-compose.yml:471
celery-redis:
    command: >
      redis-server
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru  # Different from main Redis
    mem_limit: 300m  # More memory for queue
```

2. **Worker Scaling**:
```yaml
# Horizontal scaling
celery-worker:
    deploy:
        replicas: 3  # Run 3 worker containers
    command: ["celery", "-A", "tasks", "worker", "--concurrency=2"]
```

3. **Resource Allocation**:
- **Celery workers**: 256MB RAM, 2 concurrent processes each
- **Celery Redis**: 300MB RAM (vs 100MB for main Redis)
- **Flower**: 128MB RAM for monitoring

**Deep Dive - Scaling Triggers**:
```python
# Planned auto-scaling logic
def should_scale_workers():
    queue_depth = redis.llen('celery:queue:evaluation')
    active_workers = flower_api.get_active_workers()
    avg_task_time = flower_api.get_avg_task_time()
    
    # Scale up if queue depth > workers * threshold
    if queue_depth > len(active_workers) * 10:
        return "scale_up"
    # Scale down if queue mostly empty
    elif queue_depth < len(active_workers) * 2:
        return "scale_down"
```

**Production Considerations**:
- Use Redis Cluster for queue HA
- Celery Beat for scheduled tasks (not yet implemented)
- Result backend cleanup (TTL on results)
- Prometheus metrics export

---

### Q7: How does the zero-downtime migration actually work in production?

**Answer**:
Careful orchestration ensures no task loss:

**Phase 1: Dual Write (Current)**
```python
# Both systems active
if random.random() < 0.5:
    celery_task = submit_to_celery(task)
    # Also track in legacy for comparison
    track_in_legacy(task.id, "celery")
else:
    legacy_result = submit_to_legacy(task)
```

**Phase 2: Celery Primary, Legacy Backup**
```python
# 90% Celery, legacy as fallback
try:
    if random.random() < 0.9:
        result = submit_to_celery(task)
    else:
        result = submit_to_legacy(task)
except CeleryError:
    # Fallback to legacy on Celery issues
    result = submit_to_legacy(task)
```

**Phase 3: Legacy Decommission**
```python
# Drain legacy queue
while legacy_queue.size() > 0:
    # Stop new submissions
    ACCEPT_LEGACY_TASKS = False
    # Process remaining
    process_legacy_tasks()
    
# Verify no data loss
verify_all_tasks_migrated()
```

**Deep Dive - Migration Verification**:
```python
# comparison_script.py
async def compare_systems():
    # Submit identical tasks
    celery_result = await submit_to_celery(test_task)
    legacy_result = await submit_to_legacy(test_task)
    
    # Compare execution times
    assert abs(celery_result.duration - legacy_result.duration) < 0.1
    
    # Compare outputs
    assert celery_result.output == legacy_result.output
    
    # Compare resource usage
    assert celery_result.memory_used <= legacy_result.memory_used
```

**Rollback Plan**:
1. Set `CELERY_PERCENTAGE=0` 
2. All traffic returns to legacy
3. Investigate issues while legacy handles load
4. Fix and retry migration

---

## 🟣 METR-Specific Celery Usage

### Q8: How would Celery support AI safety evaluation workloads?

**Answer**:
Celery features align with AI safety needs:

1. **Long-Running Tasks**:
```python
@celery_app.task(time_limit=3600)  # 1 hour for complex evaluations
def evaluate_ai_model(model_id, test_suite):
    # Long-running AI evaluation
    pass
```

2. **GPU Task Routing** (future):
```python
task_routes = {
    'tasks.gpu_evaluation': {
        'queue': 'gpu_queue',
        'routing_key': 'gpu.evaluation'
    }
}

# GPU-specific workers
# celery -A tasks worker -Q gpu_queue --concurrency=1
```

3. **Resource Reservation**:
```python
@celery_app.task
def reserve_resources(eval_id, requirements):
    """Reserve GPU/memory before evaluation"""
    if requirements.needs_gpu:
        gpu_id = gpu_pool.reserve(requirements.gpu_memory)
        return gpu_id
```

4. **Evaluation Chaining**:
```python
# Complex evaluation pipeline
chain = (
    reserve_resources.s(eval_id, requirements) |
    download_model.s(model_url) |
    run_safety_tests.s(test_suite) |
    cleanup_resources.s()
)
chain.apply_async()
```

**Deep Dive - AI Workload Patterns**:
- Burst during new model releases
- Long tail of safety validations  
- Need for result aggregation
- Requirement for reproducibility

Celery handles via:
- Auto-scaling workers
- Task result persistence
- Workflow management
- Deterministic task IDs

---

## Key Takeaways

1. **Celery** provides production features the custom queue lacks
2. **Gradual migration** reduces risk through percentage routing
3. **Multiple queues** enable priority and specialization
4. **Comprehensive monitoring** through Flower and logging
5. **Resilience** through retries, DLQ, circuit breakers
6. **Separate infrastructure** prevents resource contention
7. **Zero-downtime** migration through dual-write period

## Hands-On Exercises

1. **Change Traffic Split**: Modify `CELERY_PERCENTAGE` and observe routing
2. **Simulate Failures**: Stop executor service, watch Celery retry
3. **Monitor Performance**: Use Flower to find slow tasks
4. **Scale Workers**: Add more Celery workers, measure throughput
5. **Priority Testing**: Submit high and low priority tasks, verify ordering