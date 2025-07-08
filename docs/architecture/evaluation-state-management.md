# Evaluation State Management Architecture

## Current Challenge: Out-of-Order Events

In our distributed evaluation platform, we've observed that events can arrive out of order, causing evaluations to get stuck in incorrect states. For example:
- Executor publishes "completed" event
- Storage-worker processes it and updates status to "completed"
- A late "running" event arrives and overwrites the status back to "running"
- Evaluation appears stuck even though it finished successfully

## Why Events Arrive Out of Order

### Multiple Publishers
- **Celery worker**: Publishes "running" when assigning an executor
- **Executor service**: Publishes "running" when container starts, "completed" when it finishes
- These are independent processes on different machines with no coordination

### Network and Processing Delays
- Redis pub/sub doesn't guarantee ordering across different publishers
- Variable network latency between services
- Storage-worker might be processing other events when new ones arrive
- Storage service API calls can be slow, causing timing gaps

### Race Conditions
- Simple evaluations can complete in <100ms
- Meanwhile, various "running" events might still be in flight
- No global ordering or timestamp comparison

## Solution Approaches

### 1. State Machine Approach (Recommended for Now)

Define valid state transitions and reject invalid ones:

**Valid transitions:**
- `queued → running → completed` ✓
- `queued → running → failed` ✓
- `queued → failed` ✓ (immediate failure)
- `running → cancelled` ✓

**Invalid transitions (ignore):**
- `completed → running` ✗
- `failed → running` ✗
- `completed → queued` ✗

**Advantages:**
- Simple to implement and understand
- Robust against out-of-order events
- Standard practice in distributed systems
- No additional infrastructure needed

**Implementation:**
```python
TERMINAL_STATES = {"completed", "failed", "cancelled"}

async def update_evaluation_status(eval_id: str, new_status: str):
    current = await get_current_status(eval_id)
    
    # Don't update if already in terminal state
    if current in TERMINAL_STATES:
        logger.info(f"Ignoring {new_status} update for {eval_id} - already in terminal state {current}")
        return
    
    # Proceed with update
    await storage.update_status(eval_id, new_status)
```

### 2. Event Ordering (Complex)

Buffer events and process them in timestamp order:
- Requires synchronized clocks across services
- Need to define ordering windows
- Complex timeout handling
- Still can't handle clock skew perfectly

### 3. Event Sourcing (Powerful but Heavyweight)

Store all events as immutable log:
- Every state change is an event
- Current state derived by replaying events
- Perfect audit trail
- Can rebuild state at any point in time

## Future Architecture for Kubernetes/Production

### Workflow Orchestration (Recommended)

Replace Celery with purpose-built workflow orchestration:

**Options:**
1. **Temporal** (Recommended for METR)
   - Explicitly models evaluations as workflows
   - Built-in state management with strong consistency
   - Automatic retries with exponential backoff
   - Visual debugging and replay capabilities
   - Perfect for long-running evaluations with complex steps

2. **Argo Workflows**
   - Native Kubernetes integration
   - YAML-based workflow definitions
   - Good for simpler, Kubernetes-centric workflows

**Benefits:**
- Eliminates manual state management
- Built-in handling of failures and retries
- Time travel debugging
- Clear visualization of execution flow

### Service Mesh + Distributed Tracing

**Istio + Jaeger/Zipkin:**
- Automatic tracing of all service calls
- See exact request flow and timing
- Built-in retry/circuit breaker patterns
- Answers "what happened?" without event sourcing

**OpenTelemetry:**
- Standardized metrics/traces/logs
- Correlation across all services
- Performance insights

### Hybrid Approach (Best of All Worlds)

1. **State Machine** for operational state (current approach)
2. **Structured Logging** to object storage for audit trail
3. **OpenTelemetry** for observability
4. **Event Sourcing** only where needed (e.g., security audit logs)

### Kubernetes-Native Design

**Custom Resource Definitions (CRDs):**
```yaml
apiVersion: evaluations.metr.ai/v1
kind: Evaluation
metadata:
  name: eval-2024-001
spec:
  code: |
    print("Hello from K8s")
  timeout: 300
  resources:
    memory: "512Mi"
    cpu: "500m"
status:
  phase: Running
  startTime: "2024-01-01T00:00:00Z"
  executor: executor-pod-abc
```

**Operator Pattern:**
- Kubernetes operator watches Evaluation CRDs
- Manages pod lifecycle
- Updates status in CRD
- Kubernetes events provide audit trail

## Recommendation for METR

### Short Term (Current Sprint)
Implement the state machine approach:
- Add terminal state checking
- Log but ignore invalid transitions
- Simple, effective, immediate improvement

### Medium Term (2-3 Months)
Evaluate workflow orchestration:
- POC with Temporal
- Compare with current Celery implementation
- Focus on complex evaluation scenarios

### Long Term (6+ Months)
Full Kubernetes-native architecture:
- Evaluation CRDs and operators
- Service mesh for observability
- Workflow orchestration for complex evaluations
- Event sourcing for security-critical audit logs

## Security Considerations for METR

Given METR's focus on AI safety and preventing autonomous replication:

1. **Audit Trail Requirements**
   - Every execution must be traceable
   - Need to prove what code ran where and when
   - Event sourcing becomes more attractive here

2. **Workflow Boundaries**
   - Temporal/Argo can enforce strict boundaries
   - Prevent evaluations from spawning new evaluations
   - Resource limits enforced at workflow level

3. **Immutable Logs**
   - All events to append-only storage
   - Cryptographic signatures for non-repudiation
   - Separate audit service with different access controls

## Conclusion

Start simple with state machines, but architect for future migration to workflow orchestration. The beauty of the current event-driven design is that it can evolve - we can add Temporal alongside Celery, gradually migrate, and keep the same executor/storage services.

The key insight: **Don't over-engineer for hypothetical requirements, but ensure the architecture can evolve when real requirements emerge.**