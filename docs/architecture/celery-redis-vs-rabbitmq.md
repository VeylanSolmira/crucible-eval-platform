# Celery Message Broker: Redis vs RabbitMQ

## Current State: Redis with Round-Robin Queue Checking

We currently use Redis as our Celery broker with separate queues for different priority levels. Here's what actually happens:

### How Redis "Priority" Works (It Doesn't)

When Celery workers listen to multiple queues like `-Q high_priority,evaluation,batch,maintenance`, they check each queue in **round-robin** fashion:

```
Check 1: high_priority queue → Check 2: evaluation queue → 
Check 3: high_priority queue → Check 4: evaluation queue → ...
```

**Example scenario:**
- 10 normal tasks queued in `evaluation` queue
- 2 high-priority tasks arrive in `high_priority` queue
- The high-priority tasks get picked up on alternating queue checks
- They effectively "jump ahead" of ~50% of normal tasks
- This provides partial preference, not true priority

### What Doesn't Work with Redis

1. **Priority parameter is ignored**: `send_task(..., priority=10)` does nothing
2. **Queue priority values ignored**: `Queue(..., priority=10)` does nothing  
3. **No true priority ordering**: Tasks in the same queue are always FIFO
4. **No priority within queues**: Can't have high/medium/low priority within one queue

## Redis vs RabbitMQ Comparison

### Redis for Celery
**Pros:**
- Dead simple setup - already running for caching anyway
- Fast for simple queues
- Good enough for most use cases
- Minimal operational overhead

**Cons:**
- No true priority queues
- No complex routing or exchanges
- Can lose messages on crash (unless persistence configured)
- Single-threaded can bottleneck at very high scale
- Round-robin queue checking, not priority-based

### RabbitMQ for Celery
**Pros:**
- Built for messaging - true priority queues, routing, exchanges, TTLs
- Real priority support: `x-max-priority` queues
- True message durability and acknowledgments
- Better monitoring/management UI
- Sophisticated routing with topic exchanges
- Can handle complex workflows

**Cons:**
- More complex to operate - Erlang, clustering, more configuration
- Another service to run and maintain
- Requires migration effort
- Overkill for simple task queues
- Additional failure point

## Our Specific Use Case

For the evaluation platform with cancellations, Redis is probably fine because:

1. We already achieve partial prioritization with separate queues
2. The round-robin checking gives high-priority tasks ~50% preference
3. Most evaluations complete quickly anyway
4. We don't have complex routing requirements

RabbitMQ would give us:
- True priority ordering within queues
- Better message delivery guarantees  
- More sophisticated dead letter handling
- Priority-based worker consumption

But it adds:
- Operational complexity
- Another service to monitor and maintain
- Migration effort and potential downtime
- More complex debugging

## Recommendation

**Start with Redis. Switch to RabbitMQ when you hit actual limitations, not theoretical ones.**

The separate `high_priority` queue approach with round-robin checking solves the immediate need without adding infrastructure. You get meaningful (though not perfect) prioritization.

Consider RabbitMQ when you need:
- Strict priority ordering (regulatory/SLA requirements)
- Complex routing rules
- Very high scale (>1000 tasks/second)
- Advanced features like delayed messages, TTL, etc.

## Implementation Notes

### Current Workaround
```python
# Separate queues provide partial prioritization
if priority:
    queue = "high_priority"  # Gets ~50% of worker attention
else:
    queue = "evaluation"     # Shares the other ~50%
```

### Future RabbitMQ Implementation
```python
# True priority with RabbitMQ
Queue('evaluation', Exchange('tasks'), routing_key='task.eval',
      queue_arguments={'x-max-priority': 10})

# Tasks can have 0-10 priority within the same queue
send_task('eval_task', args=[...], priority=9)  # Actually works!
```

## See Also
- [Week 8 Sprint Planning - RabbitMQ Migration](../planning/sprints/week-8-crucible-platform.md#rabbitmq-migration)