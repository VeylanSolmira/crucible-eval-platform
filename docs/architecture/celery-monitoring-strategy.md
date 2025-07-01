# Celery Monitoring Strategy

## Overview

This document outlines our phased approach to monitoring Celery task processing, from basic visibility to enterprise-grade observability.

## Monitoring Phases

### Phase 1: Core Monitoring with Flower (Week 1)

**What**: Built-in Celery monitoring dashboard
**Why**: Immediate visibility with zero additional setup
**When**: Day 1 of Celery implementation

```yaml
services:
  flower:
    image: mher/flower
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=redis://celery-redis:6379/0
      - FLOWER_UNAUTHENTICATED_API=true  # For development
    depends_on:
      - celery-redis
```

**Flower Provides**:
- ✅ Real-time task monitoring
- ✅ Worker status and pool information
- ✅ Queue lengths per queue name
- ✅ Task success/failure rates
- ✅ Task execution times
- ✅ Task argument inspection
- ✅ Worker resource usage
- ✅ REST API for programmatic access

**This covers 80% of monitoring needs for most teams!**

### Phase 2: Metrics Collection with Prometheus (Week 3-4)

**What**: Time-series metrics for historical analysis
**Why**: Trending, alerting, and SLA tracking
**When**: After core Celery functionality is stable

```yaml
services:
  celery-exporter:
    image: ovalmoney/celery-exporter
    ports:
      - "9540:9540"
    environment:
      - BROKER_URL=redis://celery-redis:6379/0
      - CELERY_EXPORTER_LISTEN_ADDRESS=0.0.0.0:9540
      - CELERY_EXPORTER_LOG_LEVEL=INFO
    depends_on:
      - celery-redis

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
```

**Prometheus Configuration**:
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'celery'
    static_configs:
      - targets: ['celery-exporter:9540']

  - job_name: 'flower'
    static_configs:
      - targets: ['flower:5555']
```

**Key Metrics**:
- `celery_task_sent_total` - Tasks published to queue
- `celery_task_received_total` - Tasks received by workers
- `celery_task_started_total` - Tasks that began execution
- `celery_task_succeeded_total` - Successfully completed tasks
- `celery_task_failed_total` - Failed tasks
- `celery_task_retried_total` - Retried tasks
- `celery_task_runtime_bucket` - Task duration histogram
- `celery_queue_length` - Current queue depths

### Phase 3: Distributed Tracing with OpenTelemetry (Future)

**What**: End-to-end request tracing across services
**Why**: Debug complex multi-service interactions
**When**: Only if debugging distributed system issues

```python
# In celery_worker.py
from opentelemetry import trace
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Setup tracing
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Add OTLP exporter
otlp_exporter = OTLPSpanExporter(
    endpoint="otel-collector:4317",
    insecure=True
)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Instrument Celery
CeleryInstrumentor().instrument()
```

**Provides**:
- Request flow visualization
- Cross-service latency breakdown
- Bottleneck identification
- Error propagation tracking

## Implementation Priority

### Must Have (Week 1)
1. **Flower Dashboard**
   - Zero configuration needed
   - Immediate value
   - Shows production awareness

### Should Have (Week 3-4)
2. **Application Logs**
   ```python
   import structlog
   logger = structlog.get_logger()
   
   @app.task
   def evaluate_code(eval_id: str, code: str, language: str):
       logger.info("task.started", eval_id=eval_id, language=language)
       try:
           result = execute_evaluation(eval_id, code, language)
           logger.info("task.completed", eval_id=eval_id, duration=duration)
           return result
       except Exception as e:
           logger.error("task.failed", eval_id=eval_id, error=str(e))
           raise
   ```

3. **Basic Metrics**
   ```python
   # Simple custom metrics
   from prometheus_client import Counter, Histogram, Gauge
   
   task_counter = Counter('evaluation_tasks_total', 'Total evaluations', ['status'])
   task_duration = Histogram('evaluation_duration_seconds', 'Evaluation duration')
   queue_depth = Gauge('evaluation_queue_depth', 'Current queue depth')
   ```

### Nice to Have (Future)
4. **Prometheus + Grafana**
   - Historical trending
   - Custom dashboards
   - Alerting rules

5. **OpenTelemetry**
   - Only for complex debugging
   - Distributed tracing
   - Service dependency mapping

## Monitoring Without Over-Engineering

### Start Simple
```python
# Week 1: Just use Flower + logging
@app.task
def evaluate_code(eval_id: str, code: str, language: str):
    logger.info(f"Starting evaluation {eval_id}")
    result = execute_evaluation(eval_id, code, language)
    logger.info(f"Completed evaluation {eval_id}")
    return result
```

### Add Metrics Later
```python
# Week 3: Add basic metrics if needed
@app.task
@task_duration.time()  # Prometheus histogram
def evaluate_code(eval_id: str, code: str, language: str):
    task_counter.labels(status='started').inc()
    try:
        result = execute_evaluation(eval_id, code, language)
        task_counter.labels(status='completed').inc()
        return result
    except Exception as e:
        task_counter.labels(status='failed').inc()
        raise
```

## Key Decisions

1. **Flower First**: Provides immediate value with zero setup
2. **Prometheus Later**: Only after proving core functionality
3. **OpenTelemetry Maybe**: Only if we need distributed tracing
4. **Avoid Complexity**: Don't add monitoring that we won't use

## For METR Interview

**What to Emphasize**:
- "We use Flower for real-time monitoring"
- "We've designed for Prometheus integration when needed"
- "We understand the monitoring evolution path"
- "We avoid over-engineering early"

**What to Build**:
- Just Flower initially
- Maybe add basic Prometheus in Week 4 if time permits
- Keep OpenTelemetry as a "we would add this" discussion point

## Success Criteria

### Week 1
- ✅ Flower dashboard accessible
- ✅ Can see tasks flowing through system
- ✅ Can identify failed tasks
- ✅ Can see worker status

### Week 3 (Optional)
- ⭕ Prometheus scraping metrics
- ⭕ Basic Grafana dashboard
- ⭕ Queue depth alerts

### Future
- ⭕ Full observability stack
- ⭕ SLA monitoring
- ⭕ Automated incident response

## Remember

**Perfect monitoring of a broken system < Basic monitoring of a working system**

Focus on getting Celery working first, then enhance monitoring as needed.