# Celery Status Endpoint

## Overview

The Celery status endpoint (`/api/celery-status`) provides real-time visibility into the Celery distributed task queue system. This endpoint is critical for monitoring, debugging, and operating the asynchronous evaluation platform.

## Endpoint Details

### Request
```http
GET /api/celery-status
```

### Response
```json
{
  "enabled": true,
  "connected": true,
  "workers": 3,
  "broker_url": "redis://celery-redis:6379/0",
  "active_tasks": 12,
  "scheduled_tasks": 45,
  "registered_tasks": [
    "tasks.evaluate_code",
    "tasks.cleanup_old_evaluations",
    "tasks.monitor_dead_letter_queue"
  ],
  "worker_stats": {
    "celery@worker-1": {
      "total": 1523,
      "pool": {
        "max-concurrency": 4,
        "processes": [12345, 12346, 12347, 12348],
        "max-tasks-per-child": 1000
      }
    }
  },
  "queue_details": {
    "active": {
      "celery@worker-1": [
        {
          "id": "task-123",
          "name": "tasks.evaluate_code",
          "args": ["eval-456"],
          "time_start": 1643723400.123
        }
      ]
    },
    "scheduled": {}
  }
}
```

## Use Cases

### 1. Operations Dashboard
Frontend monitoring pages use this endpoint to display real-time cluster health:

```javascript
// React component for Celery monitoring
const CeleryMonitor = () => {
  const [status, setStatus] = useState(null);
  
  useEffect(() => {
    const interval = setInterval(async () => {
      const response = await fetch('/api/celery-status');
      const data = await response.json();
      setStatus(data);
    }, 5000); // Poll every 5 seconds
    
    return () => clearInterval(interval);
  }, []);
  
  return (
    <Dashboard>
      <Metric label="Workers" value={status?.workers || 0} />
      <Metric label="Active Tasks" value={status?.active_tasks || 0} />
      <Metric label="Queue Depth" value={status?.scheduled_tasks || 0} />
      <WorkerList workers={status?.worker_stats} />
    </Dashboard>
  );
};
```

### 2. Health Checks & Alerting

#### Kubernetes Liveness Probe
```yaml
livenessProbe:
  httpGet:
    path: /api/celery-status
    port: 8080
  periodSeconds: 30
  successThreshold: 1
  failureThreshold: 3
```

#### Monitoring Script
```bash
#!/bin/bash
# Check Celery health and alert if issues

CELERY_STATUS=$(curl -s http://api.example.com/api/celery-status)
CONNECTED=$(echo $CELERY_STATUS | jq -r '.connected')
WORKERS=$(echo $CELERY_STATUS | jq -r '.workers')
ACTIVE_TASKS=$(echo $CELERY_STATUS | jq -r '.active_tasks')

if [ "$CONNECTED" != "true" ]; then
  alert_pagerduty "Celery disconnected from broker"
fi

if [ "$WORKERS" -lt 2 ]; then
  alert_slack "Low Celery workers: $WORKERS"
fi

if [ "$ACTIVE_TASKS" -gt 100 ]; then
  alert_slack "High active tasks: $ACTIVE_TASKS"
fi
```

### 3. Auto-Scaling Decisions

```python
# Auto-scaler service
async def check_and_scale():
    """Scale Celery workers based on queue depth."""
    response = await httpx.get("http://api:8080/api/celery-status")
    status = response.json()
    
    scheduled = status.get('scheduled_tasks', 0)
    workers = status.get('workers', 0)
    
    # Scale up if queue is deep
    if scheduled > 50 and workers < 10:
        scale_celery_workers(increase=2)
        logger.info(f"Scaling up: {scheduled} tasks queued")
    
    # Scale down if idle
    elif scheduled < 5 and workers > 2:
        scale_celery_workers(decrease=1)
        logger.info("Scaling down: Low queue depth")
```

### 4. Debugging Production Issues

Common debugging scenarios:

#### "Why is my evaluation stuck?"
```python
# Debug script
def find_stuck_evaluation(eval_id):
    status = requests.get('/api/celery-status').json()
    
    # Check active tasks
    for worker, tasks in status['queue_details']['active'].items():
        for task in tasks:
            if eval_id in task['args']:
                runtime = time.time() - task['time_start']
                print(f"Found on {worker}, running for {runtime}s")
                return
    
    # Check scheduled
    for worker, tasks in status['queue_details']['scheduled'].items():
        for task in tasks:
            if eval_id in task['args']:
                print(f"Scheduled on {worker}, waiting to run")
                return
    
    print("Not found in Celery queues")
```

#### "Are workers healthy?"
```python
def check_worker_health(status):
    for worker, stats in status['worker_stats'].items():
        pool = stats['pool']
        
        # Check process count
        if len(pool['processes']) < pool['max-concurrency']:
            print(f"WARNING: {worker} has crashed processes")
        
        # Check task throughput
        if stats['total'] < 100:  # In last period
            print(f"WARNING: {worker} low throughput")
```

### 5. Migration Monitoring

During the transition from legacy queue to Celery:

```python
class QueueRouter:
    async def route_evaluation(self, eval_id, code):
        """Route to Celery if healthy, fallback to legacy."""
        try:
            status = await self.get_celery_status()
            
            if (status['enabled'] and 
                status['connected'] and 
                status['workers'] >= 2):
                # Use Celery
                return submit_to_celery(eval_id, code)
            else:
                # Fallback to legacy
                logger.warning("Celery unhealthy, using legacy queue")
                return submit_to_legacy_queue(eval_id, code)
                
        except Exception as e:
            # Always fallback on errors
            logger.error(f"Celery status check failed: {e}")
            return submit_to_legacy_queue(eval_id, code)
```

### 6. Performance Metrics

#### Prometheus Exporter
```python
# Expose metrics for Prometheus scraping
async def export_celery_metrics():
    status = await get_celery_status()
    
    celery_workers.set(status['workers'])
    celery_active_tasks.set(status['active_tasks'])
    celery_scheduled_tasks.set(status['scheduled_tasks'])
    celery_connected.set(1 if status['connected'] else 0)
    
    # Per-worker metrics
    for worker, stats in status['worker_stats'].items():
        celery_worker_total.labels(worker=worker).set(stats['total'])
```

#### Grafana Dashboard Queries
```promql
# Queue depth over time
celery_scheduled_tasks

# Task processing rate
rate(celery_worker_total[5m])

# Worker availability
celery_workers / celery_workers_desired

# Queue saturation
celery_scheduled_tasks / (celery_workers * 4)  # 4 = concurrency
```

## Implementation Details

### Data Sources
The endpoint aggregates data from multiple Celery inspection commands:

1. `inspect.active()` - Currently executing tasks
2. `inspect.scheduled()` - Tasks waiting to run
3. `inspect.stats()` - Worker statistics
4. `inspect.registered()` - Available task types

### Performance Considerations
- Celery inspect commands can be slow with many workers
- Consider caching results for 5-10 seconds
- Use async inspection for better performance

### Error Handling
```python
@app.get("/api/celery-status")
async def get_celery_status():
    if not CELERY_ENABLED:
        return {
            "enabled": False,
            "message": "Celery is not enabled"
        }
    
    try:
        # ... inspection logic ...
    except ConnectionError:
        return {
            "enabled": True,
            "connected": False,
            "error": "Cannot connect to broker"
        }
    except Exception as e:
        logger.error(f"Celery status error: {e}")
        return {
            "enabled": True,
            "connected": False,
            "error": str(e)
        }
```

## Security Considerations

### Access Control
- Consider restricting to admin users only
- May expose sensitive task arguments
- Could reveal system capacity to attackers

### Rate Limiting
- Inspection commands are expensive
- Implement rate limiting to prevent DoS
- Cache results when possible

## Future Enhancements

### 1. Historical Metrics
Store status snapshots for trend analysis:
```python
# Every minute
status = get_celery_status()
metrics_db.insert({
    'timestamp': datetime.now(),
    'workers': status['workers'],
    'queue_depth': status['scheduled_tasks'],
    'active_tasks': status['active_tasks']
})
```

### 2. Task Search
Add ability to search for specific tasks:
```
GET /api/celery-status?task_name=evaluate_code&eval_id=123
```

### 3. WebSocket Updates
Real-time status updates without polling:
```python
@app.websocket("/ws/celery-status")
async def celery_status_ws(websocket: WebSocket):
    await websocket.accept()
    while True:
        status = await get_celery_status()
        await websocket.send_json(status)
        await asyncio.sleep(5)
```

### 4. Intelligent Alerts
- Detect queue growth trends
- Predict worker exhaustion
- Identify problematic task patterns