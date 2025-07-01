# Celery Migration Strategy

## Overview

This document outlines the strategy for migrating from the legacy in-memory queue system to Celery, a production-grade distributed task queue. The migration is designed to be gradual, safe, and reversible.

## Migration Phases

### Phase 1: Dual-Write (Current State) ✅
Both systems run in parallel with feature flags controlling traffic distribution.

```python
# Current implementation in API
if CELERY_ENABLED and random.random() < CELERY_PERCENTAGE:
    task_id = submit_evaluation_to_celery(eval_id, code, language)
else:
    # Use legacy queue
    response = await client.post(f"{QUEUE_SERVICE_URL}/tasks", ...)
```

**Benefits:**
- Zero downtime migration
- Easy rollback
- A/B testing capability
- Gradual confidence building

### Phase 2: Progressive Traffic Shift
Gradually increase Celery traffic percentage while monitoring metrics.

```yaml
# Environment variable progression
CELERY_PERCENTAGE: 0.1  # Week 1: 10%
CELERY_PERCENTAGE: 0.25 # Week 2: 25%
CELERY_PERCENTAGE: 0.5  # Week 3: 50%
CELERY_PERCENTAGE: 0.9  # Week 4: 90%
CELERY_PERCENTAGE: 1.0  # Week 5: 100%
```

**Monitoring during shift:**
- Compare completion rates
- Track performance metrics
- Monitor error rates
- Validate output consistency

### Phase 3: Celery Primary
Celery handles all traffic with legacy queue as hot standby.

```python
# Failover implementation
try:
    task_id = submit_evaluation_to_celery(eval_id, code, language)
    if not task_id:
        raise Exception("Celery submission failed")
except Exception as e:
    logger.warning(f"Celery failed, falling back: {e}")
    # Fallback to legacy queue
    await submit_to_legacy_queue(eval_id, code)
```

### Phase 4: Legacy Decommission
Remove legacy queue components after stability period.

**Checklist:**
- [ ] 30 days of stable Celery operation
- [ ] All features ported to Celery
- [ ] Backup/archive legacy code
- [ ] Update documentation
- [ ] Remove legacy containers

## Migration Components

### 1. API Gateway Changes
```python
# api/microservices_gateway.py
class EvaluationSubmitter:
    def __init__(self):
        self.celery_enabled = CELERY_ENABLED
        self.celery_percentage = float(CELERY_PERCENTAGE)
    
    async def submit_evaluation(self, eval_id, code, language):
        # Decision logic for queue selection
        use_celery = (
            self.celery_enabled and 
            random.random() < self.celery_percentage
        )
        
        if use_celery:
            return await self._submit_to_celery(eval_id, code, language)
        else:
            return await self._submit_to_legacy(eval_id, code, language)
```

### 2. Worker Migration
Legacy queue worker → Celery worker

**Legacy Worker:**
- Polls HTTP endpoint
- Single-threaded
- No retry logic
- Local state

**Celery Worker:**
- Message-driven
- Multi-process
- Built-in retries
- Distributed state

### 3. Storage Updates
Add Celery-specific fields to track task lifecycle:

```sql
ALTER TABLE evaluations ADD COLUMN celery_task_id VARCHAR(255);
ALTER TABLE evaluations ADD COLUMN retry_count INTEGER DEFAULT 0;
ALTER TABLE evaluations ADD COLUMN queue_system VARCHAR(20); -- 'legacy' or 'celery'
```

### 4. Monitoring Integration
Track both systems during migration:

```python
# Prometheus metrics
celery_tasks_submitted = Counter('celery_tasks_submitted_total')
legacy_tasks_submitted = Counter('legacy_tasks_submitted_total')
queue_selection_duration = Histogram('queue_selection_duration_seconds')
```

## Rollback Procedures

### Immediate Rollback (Phase 1-2)
```bash
# Set environment variable
export CELERY_PERCENTAGE=0
# Restart API service
docker-compose restart api-service
```

### Emergency Rollback (Phase 3)
```python
# In api/microservices_gateway.py
FORCE_LEGACY_QUEUE = os.getenv('FORCE_LEGACY_QUEUE', 'false') == 'true'

if FORCE_LEGACY_QUEUE:
    # Override all Celery logic
    return await submit_to_legacy_queue(...)
```

### Data Recovery
If Celery data needs recovery:
```python
# Script to migrate Celery tasks back to legacy
for task in celery_app.control.inspect().active():
    # Extract evaluation ID
    eval_id = task['args'][0]
    # Resubmit to legacy queue
    legacy_queue.submit(eval_id, task['args'][1])
```

## Feature Parity Checklist

Ensure Celery implementation has all legacy features:

- [x] Basic task submission
- [x] Task status tracking
- [x] Result retrieval
- [x] Error handling
- [x] Retry logic (enhanced)
- [x] Task cancellation (new)
- [x] Priority queues (new)
- [x] Dead letter queue (new)
- [ ] Metrics/monitoring
- [ ] Rate limiting

## Performance Comparison

### Legacy Queue
- **Throughput**: ~100 tasks/second
- **Latency**: 50ms submission
- **Reliability**: Single point of failure
- **Scalability**: Vertical only

### Celery
- **Throughput**: ~1000 tasks/second
- **Latency**: 10ms submission
- **Reliability**: Distributed, fault-tolerant
- **Scalability**: Horizontal (add workers)

## Risk Mitigation

### Data Loss Prevention
- Dual-write ensures no tasks lost
- Redis persistence enabled
- Task acknowledgment required
- DLQ captures failures

### Performance Degradation
- Monitor submission latency
- Alert on queue depth > 1000
- Auto-scale workers based on load
- Circuit breakers prevent cascade

### Compatibility Issues
- Extensive testing in staging
- Feature flags for quick disable
- Backwards-compatible task format
- Version tracking in metadata

## Migration Timeline

### Week 1-2: Development ✅
- Implement Celery workers
- Add retry logic
- Create cancellation API
- Set up DLQ

### Week 3-4: Testing
- Load testing both systems
- Chaos testing (kill workers)
- Feature parity validation
- Performance benchmarking

### Week 5-6: Staged Rollout
- 10% traffic to Celery
- Monitor metrics
- Fix issues
- Increase percentage

### Week 7-8: Full Migration
- 100% Celery traffic
- Legacy in standby
- Monitor stability
- Document lessons

### Week 9+: Cleanup
- Remove legacy code
- Archive documentation
- Update runbooks
- Knowledge transfer

## Success Criteria

Migration is complete when:

1. **100% traffic on Celery for 30 days**
2. **Error rate < 0.1%**
3. **P99 latency < 100ms**
4. **Zero data loss incidents**
5. **All features ported**
6. **Team trained on Celery**

## Monitoring Dashboard

Key metrics to track during migration:

```promql
# Task distribution
sum(rate(tasks_submitted_total[5m])) by (queue_system)

# Success rates
sum(rate(tasks_completed_total[5m])) by (queue_system) 
/ sum(rate(tasks_submitted_total[5m])) by (queue_system)

# Latency comparison
histogram_quantile(0.99, 
  sum(rate(task_duration_seconds_bucket[5m])) by (queue_system, le)
)

# Queue depths
celery_queue_length vs legacy_queue_length
```

## Lessons Learned

### What Worked Well
1. Dual-write pattern prevented data loss
2. Feature flags enabled quick rollback
3. Gradual rollout built confidence
4. Enhanced features (retry, DLQ) added value

### Challenges
1. Redis memory usage higher than expected
2. Worker scaling needed tuning
3. Task serialization format differences
4. Monitoring gap initially

### Recommendations
1. Start with read-heavy workloads
2. Implement comprehensive monitoring first
3. Test failure scenarios extensively
4. Document everything for operators