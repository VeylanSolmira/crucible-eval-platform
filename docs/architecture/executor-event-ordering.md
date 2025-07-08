# Executor Event Ordering Architecture

## Problem Statement

During high-load testing, we discovered that fast-executing evaluations can experience race conditions where events arrive out of order at the storage-worker service. Specifically:

1. Container completes execution before the "running" event is fully processed
2. "Completed" event arrives while evaluation is still in "provisioning" state
3. State machine correctly rejects invalid transition (provisioning → completed)
4. Evaluation gets stuck in "running" state forever

This occurred in production testing with evaluations completing in < 100ms under high concurrency.

## Current Architecture

```
Executor Service → Redis Pub/Sub → Storage Worker → Storage Service
```

Events are published immediately as they occur:
- Container allocated: publishes "provisioning"
- Container started: publishes "running"  
- Container finished: publishes "completed"

**Problem**: No guarantee of delivery order due to:
- Network latency variations
- Redis pub/sub doesn't guarantee ordering across channels
- Processing delays in storage-worker
- HTTP request latency to storage service

## Solution Options Analysis

### Option 1: Allow Provisioning → Completed Transition (Implemented as Quick Fix)

**Implementation**: Added "completed" to provisioning's allowed transitions

**Pros**:
- Simple, one-line change
- Handles reality of fast executions
- Prevents evaluations getting stuck

**Cons**:
- Loses execution tracking fidelity
- Semantic confusion (did it actually run?)
- Band-aid solution, not addressing root cause

**Verdict**: Good temporary fix, but not the long-term solution

### Option 2: Event Queue with Guaranteed Ordering (RECOMMENDED)

**Implementation**: 
```python
class EventQueue:
    def __init__(self, eval_id: str):
        self.eval_id = eval_id
        self.sequence = 0
        self.events = []
        self.published_sequence = -1
    
    def add_event(self, event_type: str, data: dict):
        event = {
            "sequence": self.sequence,
            "type": event_type,
            "data": data,
            "timestamp": time.time()
        }
        self.events.append(event)
        self.sequence += 1
        self._publish_ready_events()
    
    def _publish_ready_events(self):
        # Publish events in sequence order
        while self.events:
            next_event = min(self.events, key=lambda e: e["sequence"])
            if next_event["sequence"] == self.published_sequence + 1:
                self._publish(next_event)
                self.published_sequence = next_event["sequence"]
                self.events.remove(next_event)
            else:
                break  # Wait for missing sequence
```

**Pros**:
- Guarantees correct event order
- No lost events
- Can handle network delays gracefully
- Maintains full execution history

**Cons**:
- More complex implementation
- Requires state management in executor
- Need timeout handling for lost events
- Memory overhead for queue

**Implementation Details**:
1. Each evaluation gets an event queue in executor
2. Events are tagged with sequence numbers
3. Events published only when all prior events are sent
4. Storage-worker can also buffer out-of-order events
5. Add monitoring for queue depths and delays

### Option 3: Synchronous State Confirmation

**Implementation**: Wait for state change confirmation before proceeding

```python
async def start_container(eval_id: str):
    # Publish provisioning event
    await publish_event("provisioning", {"eval_id": eval_id})
    
    # Wait for confirmation
    await wait_for_state(eval_id, "provisioning", timeout=5)
    
    # Start container
    container = await docker.containers.run(...)
    
    # Publish running event
    await publish_event("running", {"eval_id": eval_id})
    
    # Wait for confirmation
    await wait_for_state(eval_id, "running", timeout=5)
```

**Pros**:
- Simple to understand
- Guarantees state consistency
- No complex queue management

**Cons**:
- Adds latency to every execution
- Couples executor to storage service
- More failure points
- Doesn't scale well

### Option 4: Event Sourcing with Eventual Consistency

**Implementation**: Accept all events, resolve conflicts later

**Pros**:
- Highly scalable
- Never loses events
- Can reconstruct exact timeline

**Cons**:
- Complex to implement
- Eventually consistent (not immediately)
- Requires conflict resolution logic
- May be overkill for this use case

## Recommended Solution: Event Queue with Guaranteed Ordering

After analysis, Option 2 (Event Queue) provides the best balance of:
- **Correctness**: Guarantees proper event ordering
- **Performance**: Minimal latency impact
- **Reliability**: No lost events
- **Debugging**: Full execution history preserved
- **Scalability**: Queue per evaluation, not global

### Implementation Plan

1. **Phase 1: Executor Enhancement**
   - Add EventQueue class to executor
   - Tag all events with sequence numbers
   - Buffer events until prior sequences are sent
   - Add queue metrics and monitoring

2. **Phase 2: Storage-Worker Enhancement**
   - Add optional event reordering buffer
   - Handle out-of-sequence events gracefully
   - Log warnings for large sequence gaps
   - Add timeout for missing events

3. **Phase 3: Monitoring and Alerting**
   - Dashboard for event queue depths
   - Alert on stuck evaluations
   - Metrics on out-of-order event frequency
   - Performance impact analysis

### Example Implementation

```python
# executor/event_manager.py
class EventManager:
    def __init__(self):
        self.queues: Dict[str, EventQueue] = {}
        self.redis_client = get_redis_client()
    
    async def send_event(self, eval_id: str, event_type: str, data: dict):
        if eval_id not in self.queues:
            self.queues[eval_id] = EventQueue(eval_id)
        
        queue = self.queues[eval_id]
        await queue.add_event(event_type, data)
    
    async def _publish_event(self, channel: str, event_data: dict):
        # Add sequence number to event
        await self.redis_client.publish(channel, json.dumps(event_data))

# executor/evaluation_runner.py
async def run_evaluation(eval_id: str, code: str):
    event_manager = EventManager()
    
    # Send provisioning event
    await event_manager.send_event(eval_id, "provisioning", {
        "eval_id": eval_id,
        "executor_id": EXECUTOR_ID
    })
    
    # Start container
    container = await start_container(eval_id, code)
    
    # Send running event
    await event_manager.send_event(eval_id, "running", {
        "eval_id": eval_id,
        "container_id": container.id
    })
    
    # Wait for completion
    result = await container.wait()
    
    # Send completed event
    await event_manager.send_event(eval_id, "completed", {
        "eval_id": eval_id,
        "output": result.output,
        "exit_code": result.exit_code
    })
```

## Testing Strategy

1. **Unit Tests**
   - Event queue ordering logic
   - Sequence number generation
   - Buffer overflow handling

2. **Integration Tests**
   - Fast execution race conditions
   - High concurrency scenarios
   - Network delay simulation
   - Event loss scenarios

3. **Load Tests**
   - 1000+ concurrent fast evaluations
   - Measure queue depths
   - Verify zero stuck evaluations
   - Performance regression tests

## Migration Plan

1. **Deploy executor with optional event queue** (feature flag)
2. **Test with small percentage of traffic**
3. **Monitor metrics and performance**
4. **Gradually increase traffic percentage**
5. **Remove provisioning → completed transition** (after full migration)

## Success Metrics

- Zero evaluations stuck in non-terminal states
- Event ordering violations < 0.01%
- Queue depth p99 < 10 events
- Latency impact < 5ms p99
- Memory overhead < 10MB per executor

## Future Enhancements

1. **Persistent Event Queue**: Use Redis streams for durability
2. **Event Replay**: Ability to replay events for debugging
3. **Circuit Breaker**: Skip ordering for degraded mode
4. **Event Compression**: Batch multiple events together
5. **Priority Queues**: Fast-track terminal events

## Decision Log

- **2025-07-07**: Discovered race condition in production load test
- **2025-07-07**: Added provisioning → completed as quick fix
- **2025-07-07**: Documented long-term solution options
- **TBD**: Implement event queue solution
- **TBD**: Remove quick fix after migration