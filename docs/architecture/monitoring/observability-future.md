# Observability and Tracing Future

## Current State
- Basic logging with Python's logging module
- Some structured logging in storage worker
- HTTP health endpoints for monitoring

## Future Observability Needs

### 1. Structured Logging Everywhere
```python
# Current
logger.info(f"Processing evaluation {eval_id}")

# Future with structlog
logger.info("evaluation.processing", 
    eval_id=eval_id,
    code_length=len(code),
    engine="docker",
    queue_depth=15,
    worker_id="executor-1"
)
```

Benefits:
- Machine-parseable JSON logs
- Easy to query in CloudWatch/Datadog
- Consistent field names across services
- Context propagation

### 2. Distributed Tracing (OpenTelemetry)

Especially important for the executor service to trace:
- Container creation time
- Code execution duration
- Resource usage per evaluation
- Network calls between services

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("evaluation.execute") as span:
    span.set_attribute("eval_id", eval_id)
    span.set_attribute("code_length", len(code))
    
    with tracer.start_as_current_span("container.create"):
        container = docker_client.containers.run(...)
    
    with tracer.start_as_current_span("container.execute"):
        result = container.wait()
```

### 3. Metrics (Prometheus)

Key metrics to track:
- Evaluation queue depth
- Execution duration histogram
- Container creation failures
- Memory/CPU usage per evaluation
- Event processing lag

```python
from prometheus_client import Counter, Histogram, Gauge

evaluations_total = Counter('evaluations_total', 'Total evaluations processed')
evaluation_duration = Histogram('evaluation_duration_seconds', 'Evaluation duration')
queue_depth = Gauge('queue_depth', 'Current queue depth')
```

### 4. Security Audit Logging

For METR's use case, detailed security logs:
```python
security_logger = structlog.get_logger("security")

security_logger.warning("evaluation.suspicious",
    eval_id=eval_id,
    reason="network_attempt",
    details={
        "attempted_host": "github.com",
        "blocked": True,
        "code_snippet": code[100:200]
    }
)
```

### 5. Cost Attribution

Track resource usage per evaluation:
```python
logger.info("evaluation.completed",
    eval_id=eval_id,
    resources={
        "cpu_seconds": 2.5,
        "memory_mb_seconds": 512 * 30,
        "container_count": 1,
        "estimated_cost_cents": 0.05
    }
)
```

## Implementation Priority

1. **Phase 1**: Structured logging (all services)
   - Use structlog everywhere
   - Standardize log fields
   - JSON output for log aggregation

2. **Phase 2**: Basic metrics
   - Add Prometheus to docker-compose
   - Export key metrics
   - Create Grafana dashboards

3. **Phase 3**: Distributed tracing
   - OpenTelemetry instrumentation
   - Jaeger for trace visualization
   - Trace critical paths (evaluation flow)

4. **Phase 4**: Advanced observability
   - Custom security dashboards
   - Cost tracking and alerts
   - ML-based anomaly detection

## Why This Matters for METR

When evaluating potentially adversarial AI:
- Need to detect unusual patterns
- Track resource consumption precisely
- Maintain audit trail for security reviews
- Debug complex distributed failures
- Prove isolation and security measures work

The investment in observability pays off when:
- Investigating security incidents
- Optimizing resource usage
- Debugging edge cases
- Demonstrating platform reliability
- Meeting compliance requirements