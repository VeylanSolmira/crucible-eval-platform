# Monitoring Primer: From Basics to Production

## What is Monitoring?

Monitoring is the practice of collecting, processing, aggregating, and displaying real-time quantitative data about a system. It answers the question: "What is happening in my system right now?"

### The Four Pillars of Observability

1. **Metrics** - Numeric measurements over time
2. **Logs** - Discrete events with context
3. **Traces** - Request flow through distributed systems
4. **Events** - State changes and notable occurrences

## Core Concepts

### 📊 Metrics

**What are metrics?**
- Numeric values measured over intervals of time
- Lightweight and aggregatable
- Good for trends and alerting

**Types of metrics:**
- **Counter**: Only goes up (requests served, errors)
- **Gauge**: Can go up or down (temperature, queue size)
- **Histogram**: Distribution of values (request latencies)
- **Summary**: Like histogram but with quantiles

**Example metrics:**
```
http_requests_total{method="GET", status="200"} 15823
memory_usage_bytes{instance="server-1"} 4294967296
request_duration_seconds{quantile="0.99"} 0.238
```

### 📝 Logs

**What are logs?**
- Timestamped records of discrete events
- Contain detailed context and stack traces
- Good for debugging specific issues

**Log levels:**
- ERROR: Something failed
- WARN: Something might be wrong
- INFO: Normal operations
- DEBUG: Detailed diagnostic info

**Structured vs Unstructured:**
```python
# Unstructured
print("User 123 logged in from 192.168.1.1")

# Structured (JSON)
logger.info({
    "event": "user_login",
    "user_id": 123,
    "ip": "192.168.1.1",
    "timestamp": "2024-01-15T10:30:00Z"
})
```

### 🔍 Traces

**What are traces?**
- Track requests across multiple services
- Show timing and dependencies
- Essential for microservices debugging

**Trace components:**
- **Trace**: Entire request journey
- **Span**: Single operation within a trace
- **Context**: Metadata propagated between services

### 📅 Events

**What are events?**
- Notable occurrences (deployment, config change)
- Often trigger alerts or workflows
- Bridge between monitoring and automation

## The Monitoring Pipeline

```
[Collection] → [Aggregation] → [Storage] → [Visualization] → [Alerting]
     ↓              ↓             ↓              ↓               ↓
  Collectors    Aggregators    Time-Series   Dashboards      Rules &
  Exporters     Processors     Databases     Queries       Notifications
```

## Component Deep Dive

### 🔍 Collectors

**Purpose**: Gather raw data from various sources

**Types of collectors:**

1. **System Collectors**
   ```python
   # Pseudo-code for CPU collector
   class CPUCollector:
       def collect(self):
           return {
               'cpu.usage': psutil.cpu_percent(),
               'cpu.load': os.getloadavg()[0],
               'cpu.cores': psutil.cpu_count()
           }
   ```

2. **Application Collectors**
   ```python
   # Instrumentation example
   @metrics.timer('api.request.duration')
   def handle_request(request):
       metrics.increment('api.request.count')
       try:
           result = process(request)
           metrics.increment('api.request.success')
           return result
       except Exception as e:
           metrics.increment('api.request.error')
           raise
   ```

3. **Infrastructure Collectors**
   - Kubernetes metrics (pods, nodes, deployments)
   - Cloud provider metrics (EC2, RDS, S3)
   - Network devices (routers, load balancers)

### 📊 Aggregators

**Purpose**: Process and summarize metrics before storage

**Common aggregation operations:**

1. **Time-based rollups**
   ```
   1-minute data → 5-minute averages → hourly summaries → daily reports
   ```

2. **Statistical aggregations**
   - Mean, median, percentiles
   - Min, max, sum
   - Standard deviation

3. **Sampling strategies**
   ```python
   # Reservoir sampling for high-volume metrics
   class ReservoirSampler:
       def __init__(self, size=1000):
           self.reservoir = []
           self.size = size
           self.count = 0
       
       def add(self, value):
           if len(self.reservoir) < self.size:
               self.reservoir.append(value)
           else:
               # Randomly replace elements
               j = random.randint(0, self.count)
               if j < self.size:
                   self.reservoir[j] = value
           self.count += 1
   ```

4. **Downsampling**
   - Keep recent data at high resolution
   - Progressively reduce older data resolution
   - Example: 1s → 10s → 1m → 5m → 1h

### 💾 Storage

**Purpose**: Efficiently store and query time-series data

**Storage types:**

1. **Time-Series Databases (TSDB)**
   - **Prometheus**: Pull-based, local storage
   - **InfluxDB**: High-performance writes
   - **TimescaleDB**: PostgreSQL extension
   - **VictoriaMetrics**: Prometheus-compatible, efficient

2. **Storage schemas:**
   ```sql
   -- Traditional RDBMS approach (inefficient)
   CREATE TABLE metrics (
       timestamp TIMESTAMP,
       metric_name VARCHAR(255),
       value FLOAT,
       labels JSONB
   );
   
   -- Time-series optimized
   CREATE TABLE metrics (
       time TIMESTAMPTZ NOT NULL,
       series_id INTEGER,
       value DOUBLE PRECISION
   ) PARTITION BY RANGE (time);
   ```

3. **Compression techniques:**
   - Delta encoding (store differences)
   - Gorilla compression (XOR timestamps)
   - Dictionary encoding (repeated strings)

### 📤 Exporters

**Purpose**: Send metrics to external systems

**Common exporters:**

1. **Pull-based (Prometheus style)**
   ```python
   # Expose metrics endpoint
   @app.route('/metrics')
   def metrics():
       return prometheus_client.generate_latest()
   ```

2. **Push-based (CloudWatch style)**
   ```python
   # Push to CloudWatch
   cloudwatch.put_metric_data(
       Namespace='MyApp',
       MetricData=[{
           'MetricName': 'RequestCount',
           'Value': count,
           'Unit': 'Count',
           'Timestamp': datetime.now()
       }]
   )
   ```

## Real-World Architecture Examples

### Small Application
```
App → StatsD → Graphite → Grafana
```

### Medium Kubernetes Cluster
```
Pods → Prometheus → Thanos → Grafana
     ↓
  cAdvisor
```

### Large Multi-Cloud
```
Apps/Services → Collectors → Kafka → Stream Processor → Multiple TSDBs
                    ↓                        ↓                  ↓
                 OpenTelemetry            Flink/Spark      Prometheus
                 Collectors               Aggregation       InfluxDB
                                                           Elasticsearch
```

## Monitoring Patterns

### 1. RED Method (Request-Oriented)
- **Rate**: Requests per second
- **Errors**: Error rate
- **Duration**: Response time

### 2. USE Method (Resource-Oriented)
- **Utilization**: % time resource is busy
- **Saturation**: Amount of queued work
- **Errors**: Error events

### 3. Four Golden Signals (Google SRE)
- **Latency**: Time to service requests
- **Traffic**: Demand on system
- **Errors**: Rate of failed requests
- **Saturation**: System capacity

## Best Practices

### 1. Metric Design
```python
# Bad: High cardinality
requests_total{user_id="12345", session_id="abc123"}  # Millions of combinations!

# Good: Bounded cardinality
requests_total{method="GET", status="200", service="api"}  # ~100 combinations
```

### 2. Retention Policies
```yaml
retention_policies:
  - resolution: 1s
    retention: 24h    # Keep second-level data for 1 day
  - resolution: 1m
    retention: 7d     # Keep minute-level for 1 week
  - resolution: 1h
    retention: 30d    # Keep hourly for 1 month
  - resolution: 1d
    retention: 1y     # Keep daily for 1 year
```

### 3. Alert Design
```yaml
# Good alert
alert: HighErrorRate
expr: |
  rate(http_requests_total{status=~"5.."}[5m]) > 0.05
for: 10m
labels:
  severity: warning
annotations:
  summary: "High error rate on {{ $labels.service }}"
  description: "Error rate is {{ $value | humanizePercentage }}"
```

## Common Pitfalls

1. **Metrics explosion**
   - Too many labels → cardinality explosion
   - Solution: Limit labels, use recording rules

2. **Missing data**
   - Gaps in collection → blind spots
   - Solution: Monitor the monitors

3. **Alert fatigue**
   - Too many alerts → ignored alerts
   - Solution: Alert on symptoms, not causes

4. **Storage costs**
   - Keeping all data forever
   - Solution: Implement retention policies

## Tools Comparison

| Tool | Type | Best For | Pros | Cons |
|------|------|----------|------|------|
| Prometheus | TSDB + Collector | Kubernetes | Free, powerful queries | Single-node storage |
| Grafana | Visualization | Any data source | Beautiful dashboards | Just visualization |
| Datadog | Full platform | SaaS preference | All-in-one | Expensive at scale |
| ELK Stack | Logs + Metrics | Log analysis | Powerful search | Resource heavy |
| CloudWatch | Cloud native | AWS workloads | AWS integration | AWS lock-in |

## Getting Started Checklist

- [ ] **Define what to monitor**
  - Start with the Four Golden Signals
  - Add business metrics
  - Include infrastructure basics

- [ ] **Choose collection method**
  - Push vs Pull
  - Agent vs Agentless
  - SDK instrumentation

- [ ] **Select storage solution**
  - Expected data volume
  - Query requirements
  - Retention needs

- [ ] **Design dashboards**
  - Overview dashboard
  - Service-specific views
  - Investigation dashboards

- [ ] **Configure alerts**
  - Start with critical paths
  - Use symptom-based alerts
  - Include runbooks

- [ ] **Plan for growth**
  - Aggregation strategies
  - Federation/sharding
  - Cost management

## Example: Monitoring Evolution

### Stage 1: Basic Logging
```python
print(f"[{datetime.now()}] Processing evaluation {eval_id}")
```

### Stage 2: Metrics Library
```python
import prometheus_client

requests_total = Counter('requests_total', 'Total requests')
request_duration = Histogram('request_duration_seconds', 'Request duration')

@request_duration.time()
def process_request():
    requests_total.inc()
    # ... process ...
```

### Stage 3: Full Observability
```python
from opentelemetry import trace, metrics

tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

request_counter = meter.create_counter("requests", "Number of requests")

@tracer.start_as_current_span("process_request")
def process_request(request_id):
    span = trace.get_current_span()
    span.set_attribute("request.id", request_id)
    
    request_counter.add(1, {"method": "POST"})
    
    # Structured logging with trace context
    logger.info("Processing request", extra={
        "request_id": request_id,
        "trace_id": span.get_span_context().trace_id
    })
```

## Summary

Monitoring is not just about collecting data—it's about gaining actionable insights into your system's behavior. Start simple with basic metrics and logs, then evolve based on your needs. Remember: you can't improve what you don't measure, but measuring everything doesn't mean you understand anything. Focus on metrics that drive decisions and improve reliability.