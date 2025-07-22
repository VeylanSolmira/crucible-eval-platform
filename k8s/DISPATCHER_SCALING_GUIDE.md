# Dispatcher Autoscaling Guide

## Overview

This guide explores different approaches to automatically scale the dispatcher service based on workload demands. The dispatcher creates Kubernetes Jobs for code evaluations, and its capacity directly impacts evaluation throughput.

## Scaling Signals

### 1. Queue Depth (Most Common)

Monitor the number of pending tasks in the Celery queue.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: dispatcher-hpa
spec:
  scaleTargetRef:
    kind: Deployment
    name: dispatcher
  minReplicas: 1
  maxReplicas: 20
  metrics:
  - type: External
    external:
      metric:
        name: celery_queue_length
        selector:
          matchLabels:
            queue_name: "evaluation"
      target:
        type: AverageValue
        averageValue: "10"  # Scale up if >10 tasks per dispatcher
```

**Pros**: 
- Direct correlation to pending work
- Easy to understand and tune

**Cons**: 
- Requires exposing Celery/Redis metrics
- Doesn't account for task complexity

### 2. Task Wait Time

Scale based on how long tasks wait in queue before processing.

```yaml
metrics:
- type: External
  external:
    metric:
      name: celery_task_wait_time_seconds
    target:
      type: AverageValue
      averageValue: "5"  # Scale if tasks wait >5 seconds
```

**Pros**: 
- Directly measures user experience impact
- Accounts for processing speed

**Cons**: 
- More complex to calculate accurately
- May have lag in measurements

### 3. HTTP Request Rate

Scale based on incoming requests to dispatcher.

```yaml
metrics:
- type: Pods
  pods:
    metric:
      name: http_requests_per_second
    target:
      type: AverageValue
      averageValue: "100"  # 100 requests/second per pod
```

**Pros**: 
- Simple to implement
- Built into most ingress controllers

**Cons**: 
- Doesn't account for queue backlog
- May scale unnecessarily for health checks

### 4. Composite Metrics

Combine multiple signals for smarter scaling.

```yaml
metrics:
# Scale on multiple signals
- type: Resource
  resource:
    name: cpu
    target:
      averageUtilization: 70
- type: External
  external:
    metric:
      name: celery_queue_length
    target:
      averageValue: "20"
behavior:
  scaleUp:
    selectPolicy: Max  # Use most aggressive scaling signal
  scaleDown:
    selectPolicy: Min  # Conservative scale-down
```

## Implementation Approaches

### Approach 1: KEDA (Recommended)

[KEDA](https://keda.sh/) (Kubernetes Event Driven Autoscaling) is purpose-built for queue-based scaling.

#### Installation
```bash
kubectl apply -f https://github.com/kedacore/keda/releases/download/v2.11.0/keda-2.11.0.yaml
```

#### Basic Configuration
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: dispatcher-scaler
spec:
  scaleTargetRef:
    name: dispatcher
  minReplicaCount: 1
  maxReplicaCount: 50
  triggers:
  - type: redis
    metadata:
      address: redis:6379
      listName: celery  # Celery queue name
      listLength: "10"  # Target queue length per instance
```

#### Advanced Configuration with Scale-to-Zero
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: dispatcher-scaler
spec:
  scaleTargetRef:
    name: dispatcher
  minReplicaCount: 0  # Scale to zero!
  maxReplicaCount: 50
  cooldownPeriod: 300  # 5 min cooldown
  triggers:
  - type: redis
    metadata:
      address: redis:6379
      listName: celery
      listLength: "10"
      activationListLength: "1"  # Wake from 0 if any items
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleUp:
          stabilizationWindowSeconds: 30
          policies:
          - type: Percent
            value: 100  # Double pods
            periodSeconds: 30
          - type: Pods
            value: 5    # Or add 5 pods
            periodSeconds: 30
          selectPolicy: Max
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10  # Remove 10% of pods
            periodSeconds: 60
```

### Approach 2: Custom Metrics API

Build your own metrics endpoint for fine-grained control.

#### Metrics Server
```python
# metrics_server.py
from prometheus_client import Gauge, generate_latest
from flask import Flask
import redis
import time

app = Flask(__name__)

# Define metrics
queue_depth = Gauge('celery_queue_depth', 'Number of pending tasks')
avg_wait_time = Gauge('celery_avg_wait_time', 'Average task wait time')
oldest_task_age = Gauge('celery_oldest_task_age', 'Age of oldest task in queue')

def calculate_metrics():
    r = redis.Redis(host='redis', port=6379)
    
    # Queue depth
    depth = r.llen('celery')
    queue_depth.set(depth)
    
    # Get task timestamps from queue
    tasks = r.lrange('celery', 0, -1)
    if tasks:
        # Parse task headers for timestamp
        # (Implementation depends on Celery message format)
        oldest_timestamp = min(task['timestamp'] for task in tasks)
        oldest_age = time.time() - oldest_timestamp
        oldest_task_age.set(oldest_age)
        
        # Calculate average wait time
        total_wait = sum(time.time() - task['timestamp'] for task in tasks)
        avg_wait_time.set(total_wait / len(tasks))

@app.route('/metrics')
def metrics():
    calculate_metrics()
    return generate_latest()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9090)
```

#### Prometheus Adapter Configuration
```yaml
# prometheus-adapter-config.yaml
rules:
- seriesQuery: 'celery_queue_depth'
  resources:
    overrides:
      namespace: {resource: "namespace"}
  name:
    matches: "^celery_(.*)$"
    as: "${1}"
  metricsQuery: '<<.Series>>{<<.LabelMatchers>>}'
```

### Approach 3: Application-Level Scaling

Implement scaling logic directly in your application.

```python
# autoscaler.py
from kubernetes import client, config
import redis
import time
import logging

logger = logging.getLogger(__name__)

class DispatcherAutoscaler:
    def __init__(self):
        config.load_incluster_config()
        self.apps_v1 = client.AppsV1Api()
        self.redis_client = redis.Redis(host='redis', port=6379)
        
        # Scaling parameters
        self.min_replicas = 1
        self.max_replicas = 50
        self.tasks_per_replica = 10
        self.scale_down_threshold = 0.5  # 50% idle capacity
        
    def get_current_replicas(self):
        deployment = self.apps_v1.read_namespaced_deployment(
            name="dispatcher",
            namespace="crucible"
        )
        return deployment.spec.replicas
    
    def calculate_desired_replicas(self):
        queue_depth = self.redis_client.llen('celery')
        desired = max(
            self.min_replicas,
            min(self.max_replicas, queue_depth // self.tasks_per_replica)
        )
        return desired
    
    def scale_deployment(self, replicas):
        patch = {"spec": {"replicas": replicas}}
        self.apps_v1.patch_namespaced_deployment(
            name="dispatcher",
            namespace="crucible",
            body=patch
        )
        logger.info(f"Scaled dispatcher to {replicas} replicas")
    
    def run_scaling_loop(self):
        while True:
            try:
                current = self.get_current_replicas()
                desired = self.calculate_desired_replicas()
                
                if desired != current:
                    # Add hysteresis to prevent flapping
                    if desired > current or desired < current * self.scale_down_threshold:
                        self.scale_deployment(desired)
                
            except Exception as e:
                logger.error(f"Scaling error: {e}")
            
            time.sleep(30)  # Check every 30 seconds

if __name__ == "__main__":
    autoscaler = DispatcherAutoscaler()
    autoscaler.run_scaling_loop()
```

### Approach 4: Event-Driven Scaling

React to Celery events in real-time.

```python
# event_scaler.py
from celery import Celery
from celery.signals import task_sent, task_success, task_failure
from kubernetes import client, config
import threading
import time

class EventDrivenScaler:
    def __init__(self):
        self.pending_tasks = 0
        self.last_scale_time = 0
        self.scale_cooldown = 60  # seconds
        self.lock = threading.Lock()
        
        # K8s client
        config.load_incluster_config()
        self.apps_v1 = client.AppsV1Api()
        
    @task_sent.connect
    def on_task_sent(self, sender=None, headers=None, **kwargs):
        with self.lock:
            self.pending_tasks += 1
            self.check_scale_up()
    
    @task_success.connect
    @task_failure.connect
    def on_task_complete(self, sender=None, **kwargs):
        with self.lock:
            self.pending_tasks = max(0, self.pending_tasks - 1)
            self.check_scale_down()
    
    def check_scale_up(self):
        if time.time() - self.last_scale_time < self.scale_cooldown:
            return
            
        if self.pending_tasks > self.get_capacity():
            self.scale_up()
    
    def check_scale_down(self):
        if time.time() - self.last_scale_time < self.scale_cooldown:
            return
            
        if self.pending_tasks < self.get_capacity() * 0.3:
            self.scale_down()
    
    def get_capacity(self):
        deployment = self.apps_v1.read_namespaced_deployment(
            name="dispatcher", namespace="crucible"
        )
        return deployment.spec.replicas * 10  # 10 tasks per replica
    
    def scale_up(self):
        # Implementation here
        self.last_scale_time = time.time()
    
    def scale_down(self):
        # Implementation here
        self.last_scale_time = time.time()
```

## Recommendation: KEDA with Redis Trigger

For the Crucible platform, **KEDA with Redis trigger** is the recommended approach:

### Why KEDA?

1. **Purpose-built**: Designed specifically for queue-based autoscaling
2. **No custom code**: Pure YAML configuration
3. **Battle-tested**: Widely used with Celery and Redis
4. **Feature-rich**: Scale-to-zero, multiple triggers, advanced behaviors
5. **Maintained**: Active community and regular updates

### Implementation Steps

1. **Install KEDA**
   ```bash
   kubectl apply -f https://github.com/kedacore/keda/releases/download/v2.11.0/keda-2.11.0.yaml
   ```

2. **Create ScaledObject**
   ```yaml
   # dispatcher-scaledobject.yaml
   apiVersion: keda.sh/v1alpha1
   kind: ScaledObject
   metadata:
     name: dispatcher-scaler
     namespace: crucible
   spec:
     scaleTargetRef:
       name: dispatcher
     minReplicaCount: 1
     maxReplicaCount: 20
     triggers:
     - type: redis
       metadata:
         address: redis:6379
         listName: celery
         listLength: "10"
   ```

3. **Apply and Monitor**
   ```bash
   kubectl apply -f dispatcher-scaledobject.yaml
   kubectl get hpa
   kubectl get pods -w
   ```

### Production Configuration

For production, use this enhanced configuration:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: dispatcher-scaler
  namespace: crucible
spec:
  scaleTargetRef:
    name: dispatcher
  minReplicaCount: 2  # Minimum for HA
  maxReplicaCount: 100
  cooldownPeriod: 300  # 5 minutes
  triggers:
  - type: redis
    metadata:
      address: redis:6379
      password: "${REDIS_PASSWORD}"  # From secret
      listName: celery
      listLength: "15"
      enableTLS: "false"
      databaseIndex: "0"
  - type: prometheus  # Secondary trigger
    metadata:
      serverAddress: http://prometheus:9090
      metricName: http_request_duration_seconds
      threshold: "0.5"
      query: |
        histogram_quantile(0.95,
          rate(http_request_duration_seconds_bucket{job="dispatcher"}[1m])
        )
```

## Monitoring and Alerting

### Key Metrics to Track

1. **Scaling Metrics**
   - Current vs desired replicas
   - Scale-up/down frequency
   - Time to scale

2. **Performance Metrics**
   - Queue depth over time
   - Task wait time
   - Dispatcher response time

3. **Cost Metrics**
   - Pod hours consumed
   - Resource utilization
   - Cost per evaluation

### Example Alerts

```yaml
# prometheus-alerts.yaml
groups:
- name: dispatcher-scaling
  rules:
  - alert: DispatcherScalingMaxed
    expr: |
      keda_scaler_metrics_value{scaler="redis"} 
      > keda_scaler_max_replicas{scaler="redis"} * 0.9
    for: 5m
    annotations:
      summary: "Dispatcher scaling is near maximum capacity"
      
  - alert: QueueBacklogHigh
    expr: redis_list_length{list="celery"} > 1000
    for: 10m
    annotations:
      summary: "Celery queue backlog is critically high"
```

## Testing Scaling Behavior

### Load Testing Script

```python
# load_test.py
import asyncio
import httpx
import random
import time

async def submit_evaluation(client, i):
    code = f"print('Test evaluation {i}')"
    response = await client.post(
        "http://api-service/api/eval",
        json={"code": code, "language": "python"}
    )
    return response.status_code

async def load_test(rate_per_second, duration_seconds):
    async with httpx.AsyncClient() as client:
        tasks = []
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            # Submit batch of evaluations
            batch_size = int(rate_per_second / 10)  # 10 batches per second
            for i in range(batch_size):
                task = submit_evaluation(client, i)
                tasks.append(task)
            
            await asyncio.sleep(0.1)  # 100ms between batches
        
        # Wait for all submissions to complete
        results = await asyncio.gather(*tasks)
        success_rate = sum(1 for r in results if r == 200) / len(results)
        
        print(f"Submitted {len(results)} evaluations")
        print(f"Success rate: {success_rate:.2%}")

# Test scaling behavior
asyncio.run(load_test(rate_per_second=50, duration_seconds=300))
```

## Conclusion

Autoscaling the dispatcher service is crucial for handling variable workloads efficiently. KEDA provides the best balance of features, simplicity, and reliability for queue-based autoscaling. Start with basic queue depth scaling and evolve to more sophisticated strategies as you understand your workload patterns better.