# Monitoring Architecture

## Overview

The monitoring system provides observability into evaluation executions, system health, and performance metrics. It follows a modular architecture designed to scale from simple in-memory storage to full observability platforms.

## Current Implementation

The MVP uses a monolithic `AdvancedMonitor` that provides:
- Event emission and storage
- Real-time event streaming via queue-based subscriptions
- Thread-safe operations
- In-memory storage

## Future Architecture: Collectors & Exporters

### 🔍 Collectors
Components that gather metrics from various sources.

**Types of Collectors:**

1. **System Collectors**
   - CPU usage per evaluation
   - Memory consumption
   - Disk I/O metrics
   - Network traffic (if allowed)

2. **Container Collectors**
   - Docker stats API integration
   - cgroups metrics
   - Container lifecycle events
   - Resource limit violations

3. **Application Collectors**
   - Evaluation start/complete events
   - Code execution time
   - Queue depth and processing rate
   - Error rates and types

4. **Custom Collectors**
   - Model-specific metrics (for AI evaluations)
   - Security events (sandbox violations)
   - Business metrics (evaluations per user)

**Collector Interface:**
```python
class MetricCollector(ABC):
    @abstractmethod
    def collect(self) -> List[Metric]:
        """Collect current metrics"""
        pass
    
    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Return collector metadata"""
        pass
```

### 📤 Exporters
Components that send metrics to external monitoring systems.

**Types of Exporters:**

1. **Time-Series Databases**
   - **Prometheus Exporter**: Expose metrics endpoint
   - **InfluxDB Exporter**: Batch write to InfluxDB
   - **TimescaleDB Exporter**: PostgreSQL time-series

2. **Cloud Monitoring**
   - **CloudWatch Exporter**: AWS metrics
   - **Stackdriver Exporter**: GCP monitoring
   - **Azure Monitor Exporter**: Azure metrics

3. **Logging Systems**
   - **Elasticsearch Exporter**: For log aggregation
   - **Splunk Exporter**: Enterprise logging
   - **Datadog Exporter**: Full-stack monitoring

4. **Event Streaming**
   - **Kafka Exporter**: Stream to Kafka topics
   - **Redis Streams**: Real-time event streaming
   - **NATS Exporter**: Lightweight messaging

**Exporter Interface:**
```python
class MetricExporter(ABC):
    @abstractmethod
    def export(self, metrics: List[Metric]) -> None:
        """Export metrics to external system"""
        pass
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure exporter settings"""
        pass
```

### 📈 Aggregators
Components that process and transform metrics before storage.

**Types of Aggregators:**

1. **Stream Aggregators**
   - Process metrics in real-time
   - Compute running averages, rates
   - Example: Telegraf, Fluentd

2. **Batch Aggregators**
   - Process metrics in time windows
   - Compute percentiles, histograms
   - Example: Spark, Flink

3. **Rule-based Aggregators**
   - Apply recording rules
   - Pre-compute expensive queries
   - Example: Prometheus recording rules

**Aggregator Interface:**
```python
class MetricAggregator(ABC):
    @abstractmethod
    def aggregate(self, metrics: List[Metric], window: TimeWindow) -> List[Metric]:
        """Aggregate metrics within time window"""
        pass
    
    @abstractmethod
    def get_aggregation_rules(self) -> List[AggregationRule]:
        """Return configured aggregation rules"""
        pass
```

### 💾 Storage
Components that persist time-series data efficiently.

**Types of Storage:**

1. **Local Time-Series DB**
   - Prometheus (2 hours to 15 days typical)
   - Single-node, pull-based
   - Built-in compression

2. **Distributed TSDB**
   - Thanos, Cortex (long-term Prometheus)
   - M3DB (Uber's distributed TSDB)
   - VictoriaMetrics Cluster

3. **Cloud Time-Series**
   - AWS Timestream
   - Azure Time Series Insights
   - Google Cloud Monitoring

4. **Hybrid Storage**
   - Hot data in memory/SSD
   - Warm data in cheaper storage
   - Cold data in object storage (S3)

**Storage Interface:**
```python
class MetricStorage(ABC):
    @abstractmethod
    def write(self, metrics: List[Metric]) -> None:
        """Write metrics to storage"""
        pass
    
    @abstractmethod
    def query(self, query: MetricQuery) -> List[TimeSeries]:
        """Query metrics from storage"""
        pass
    
    @abstractmethod
    def retention_policy(self) -> RetentionPolicy:
        """Get retention configuration"""
        pass
```

## Architecture Patterns

### 1. Push vs Pull Model

**Pull Model (Prometheus-style):**
```
Collectors -> Metric Registry <- Prometheus Scraper
```
- Collectors register metrics
- External system polls for metrics
- Good for: Kubernetes environments

**Push Model (CloudWatch-style):**
```
Collectors -> Aggregator -> Exporter -> CloudWatch
```
- Metrics pushed to external system
- Good for: Serverless, ephemeral workloads

### 2. Complete Metric Pipeline

```
[Collect] -> [Transform] -> [Aggregate] -> [Store] -> [Query] -> [Visualize]
    |            |              |            |          |            |
 Raw Data    Normalize     Time Window   Time-Series  PromQL    Grafana
  Events     Enrich        Statistics      TSDB      SQL       Kibana
  Metrics    Filter        Downsample    Retention   API      DataDog

                                            ↓
                                        [Export]
                                            |
                                    External Systems
                                    Alert Manager
                                    Other TSDBs
```

### 3. Aggregation Patterns

**Pre-aggregation (Recording Rules):**
```yaml
# Prometheus recording rule example
groups:
  - name: aggregations
    interval: 30s
    rules:
      # Pre-calculate 5m rate
      - record: instance:request_rate5m
        expr: rate(http_requests_total[5m])
      
      # Pre-calculate service-level percentiles
      - record: service:request_duration:p99
        expr: histogram_quantile(0.99, sum(rate(request_duration_bucket[5m])) by (service, le))
```

**Stream Processing Aggregation:**
```python
class StreamAggregator:
    def __init__(self, window_size=60):  # 60 second windows
        self.windows = defaultdict(lambda: {
            'count': 0,
            'sum': 0,
            'min': float('inf'),
            'max': float('-inf')
        })
    
    def add_metric(self, metric_name: str, value: float, timestamp: int):
        window_key = timestamp // self.window_size
        window = self.windows[f"{metric_name}:{window_key}"]
        
        window['count'] += 1
        window['sum'] += value
        window['min'] = min(window['min'], value)
        window['max'] = max(window['max'], value)
    
    def get_aggregates(self, metric_name: str, window_timestamp: int):
        window_key = window_timestamp // self.window_size
        window = self.windows.get(f"{metric_name}:{window_key}")
        
        if not window or window['count'] == 0:
            return None
        
        return {
            'avg': window['sum'] / window['count'],
            'min': window['min'],
            'max': window['max'],
            'count': window['count']
        }
```

### 4. Storage Optimization Patterns

**Downsampling Strategy:**
```python
class DownsamplingStorage:
    def __init__(self):
        self.retention_policies = [
            {'resolution': '1s', 'retention': '1h', 'storage': 'memory'},
            {'resolution': '10s', 'retention': '24h', 'storage': 'ssd'},
            {'resolution': '1m', 'retention': '7d', 'storage': 'ssd'},
            {'resolution': '5m', 'retention': '30d', 'storage': 'hdd'},
            {'resolution': '1h', 'retention': '1y', 'storage': 's3'}
        ]
    
    def downsample(self, metrics: List[Metric], from_res: str, to_res: str):
        # Group metrics by the target resolution
        # Apply aggregation function (avg, max, min, etc.)
        pass
```

**Compression Example:**
```python
class TimeSeriesCompressor:
    def compress_timestamps(self, timestamps: List[int]) -> bytes:
        """Delta-of-delta encoding for timestamps"""
        if not timestamps:
            return b''
        
        result = [timestamps[0]]  # Store first timestamp
        prev_delta = 0
        
        for i in range(1, len(timestamps)):
            delta = timestamps[i] - timestamps[i-1]
            delta_of_delta = delta - prev_delta
            result.append(delta_of_delta)
            prev_delta = delta
        
        return self.encode_varints(result)
    
    def compress_values(self, values: List[float]) -> bytes:
        """XOR compression for floating point values"""
        # Facebook's Gorilla compression algorithm
        pass
```

### 5. Multi-Exporter Pattern

```python
class MonitoringPipeline:
    def __init__(self):
        self.collectors = []
        self.exporters = []
        self.transformers = []
    
    def add_collector(self, collector: MetricCollector):
        self.collectors.append(collector)
    
    def add_exporter(self, exporter: MetricExporter):
        self.exporters.append(exporter)
    
    def run(self):
        metrics = []
        for collector in self.collectors:
            metrics.extend(collector.collect())
        
        # Transform metrics
        for transformer in self.transformers:
            metrics = transformer.transform(metrics)
        
        # Export to all configured exporters
        for exporter in self.exporters:
            exporter.export(metrics)
```

## Implementation Roadmap

### Phase 1: Current MVP ✅
- In-memory event storage
- Real-time event streaming
- Basic event types

### Phase 2: Metrics Collection
- Add system metrics collector
- Add container metrics collector
- Create metric aggregation layer

### Phase 3: First Exporter
- Implement Prometheus exporter
- Add Grafana dashboards
- Create alerting rules

### Phase 4: Cloud Integration
- Add CloudWatch exporter
- Implement auto-scaling based on metrics
- Add cost tracking metrics

### Phase 5: Full Observability
- Distributed tracing (OpenTelemetry)
- Log aggregation pipeline
- Unified observability dashboard

## Configuration Example

```yaml
monitoring:
  collectors:
    - type: system
      interval: 10s
      metrics:
        - cpu_usage
        - memory_usage
        - disk_io
    
    - type: docker
      interval: 30s
      metrics:
        - container_stats
        - container_events
    
    - type: application
      interval: 5s
      metrics:
        - evaluation_count
        - error_rate
        - queue_depth
  
  exporters:
    - type: prometheus
      endpoint: /metrics
      port: 9090
    
    - type: cloudwatch
      namespace: Crucible/Evaluations
      region: us-east-1
      batch_size: 100
    
    - type: elasticsearch
      url: http://elasticsearch:9200
      index: crucible-metrics
```

## Metric Types

### Counter
Monotonically increasing value (e.g., total evaluations)
```python
evaluations_total = Counter('evaluations_total', 'Total number of evaluations')
```

### Gauge
Value that can go up or down (e.g., queue depth)
```python
queue_depth = Gauge('queue_depth', 'Current queue depth')
```

### Histogram
Distribution of values (e.g., evaluation duration)
```python
evaluation_duration = Histogram('evaluation_duration_seconds', 'Evaluation duration')
```

### Summary
Similar to histogram but with quantiles
```python
response_time = Summary('response_time_seconds', 'Response time')
```

## Best Practices

1. **Metric Naming**
   - Use consistent prefixes (e.g., `crucible_`)
   - Include units in name (e.g., `_seconds`, `_bytes`)
   - Use lowercase with underscores

2. **Label Usage**
   - Keep cardinality low
   - Use static labels for grouping
   - Avoid user IDs or evaluation IDs as labels

3. **Collection Frequency**
   - System metrics: 10-30 seconds
   - Application metrics: 5-60 seconds
   - Batch exports to reduce overhead

4. **Resource Management**
   - Set metric retention policies
   - Implement metric sampling for high-volume data
   - Use aggregation to reduce storage

## Security Considerations

1. **Metric Access Control**
   - Authenticate metric endpoints
   - Use TLS for metric transport
   - Implement RBAC for dashboards

2. **Sensitive Data**
   - Never include secrets in metrics
   - Anonymize user data
   - Audit metric access

3. **Resource Limits**
   - Limit metric cardinality
   - Set memory limits for collectors
   - Implement circuit breakers

## Example: Adding a New Collector

```python
class GPUMetricsCollector(MetricCollector):
    def __init__(self):
        self.gpu_usage = Gauge('gpu_usage_percent', 'GPU usage percentage')
        self.gpu_memory = Gauge('gpu_memory_bytes', 'GPU memory usage')
    
    def collect(self) -> List[Metric]:
        metrics = []
        
        # Collect GPU metrics (pseudo-code)
        for gpu_id, stats in enumerate(get_gpu_stats()):
            labels = {'gpu_id': str(gpu_id)}
            metrics.append(self.gpu_usage.labels(**labels).set(stats.usage))
            metrics.append(self.gpu_memory.labels(**labels).set(stats.memory))
        
        return metrics
    
    def get_metadata(self) -> Dict[str, Any]:
        return {
            'name': 'gpu_metrics',
            'version': '1.0',
            'metrics': ['gpu_usage_percent', 'gpu_memory_bytes']
        }
```

## Testing Strategy

1. **Unit Tests**
   - Test each collector independently
   - Mock external dependencies
   - Verify metric accuracy

2. **Integration Tests**
   - Test full pipeline (collect -> export)
   - Verify data in external systems
   - Test failure scenarios

3. **Load Tests**
   - Test high-cardinality scenarios
   - Verify performance under load
   - Check memory usage

## Migration Path

From current `AdvancedMonitor` to full observability:

1. **Extract interfaces** - Define Collector/Exporter contracts
2. **Wrap existing** - Create collector for current events
3. **Add Prometheus** - First exporter for metrics
4. **Incremental adoption** - Add collectors one by one
5. **Deprecate old** - Phase out in-memory storage

This architecture provides a clear path from the current MVP to a production-grade observability platform while maintaining backward compatibility.