---
title: 'Celery Integration: A Distributed Systems Story'
duration: 3
tags: ['celery', 'distributed-systems', 'week-4']
---

## Celery Integration: Zero-Downtime Migration

### The Challenge
- Legacy queue service was a bottleneck
- Needed enterprise-grade task queue
- Could not afford downtime during migration

### The Solution: 50/50 Traffic Split
```python
if ENABLE_CELERY and random.random() < CELERY_TRAFFIC_PERCENTAGE:
    # Route to Celery
    task = celery_client.submit_evaluation.delay(eval_request)
else:
    # Route to legacy queue
    queue_client.submit(eval_request)
```

### Gradual Migration
1. **0% → 10%**: Test with small traffic
2. **10% → 50%**: Validate at scale
3. **50% → 90%**: Build confidence
4. **90% → 100%**: Complete migration
5. **Remove legacy**: Clean architecture

---

## The Idempotency Challenge

### Edge Case Discovery
```python
# Celery calls BOTH callbacks in rare cases!
@app.task
def execute_evaluation(eval_id):
    return {"status": "success"}

execute_evaluation.apply_async(
    link=release_executor.s(executor_id),      # Called on success
    link_error=release_executor.s(executor_id) # Also called (!!)
)
```

### Root Cause
- Network timeout during result acknowledgment
- Celery retries the task
- Both success AND error callbacks fire
- Executor released twice → negative capacity!

### The Fix: Atomic Operations
```lua
-- Redis Lua script for atomic release
local current = redis.call('GET', KEYS[1])
if current and current == ARGV[1] then
    redis.call('DEL', KEYS[1])
    redis.call('INCR', KEYS[2])
    return 1
end
return 0
```

**Result**: 100% reliability, zero double-releases