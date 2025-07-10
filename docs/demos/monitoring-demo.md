# Monitoring Demo - Flower Dashboard

## Overview
This demo shows how to monitor the Celery task queue and workers using the Flower dashboard.

## Current Status
⚠️ **Partial Functionality**: Flower is running with API access but UI limitations:
- ✅ Dashboard loads at http://localhost:5555
- ✅ Authentication works (admin/changeme)
- ❌ Workers tab shows 404
- ❌ Broker tab shows 404  
- ❌ Tasks tab shows 404
- ✅ API endpoints work (e.g., /api/tasks returns data)

### What Actually Works:
- **API Access**: Can query task data via API
  ```bash
  curl -u admin:changeme http://localhost:5555/api/tasks
  ```
- **Task Data**: Full task history with args, results, timestamps
- **Health Check**: `/healthcheck` endpoint
- **Authentication**: Basic auth protection

### Why the 404s:
The Flower web UI expects the Celery app to be fully initialized with task definitions. Without access to our `tasks.py`, it can't render the UI properly, but the API still functions because it just queries Redis.

### What Will Work After Full Integration:
- **Active Workers Display**: See worker names, status, and current tasks
- **Task History**: Full task details including arguments, results, and tracebacks
- **Queue Status**: Detailed queue lengths, task priorities, and routing
- **Broker Stats**: Message rates, queue backlogs, consumer status

## Demo Steps

### 1. Access Flower Dashboard
```bash
# Open in browser
open http://localhost:5555

# Login credentials:
# Username: admin
# Password: changeme
```

### 2. View Active Tasks
1. Navigate to the "Tasks" tab
2. You should see recent tasks like:
   - `tasks.assign_executor`
   - `tasks.evaluate_code`
   - `tasks.release_executor_task`

### 3. Submit Test Evaluations
```bash
# Submit multiple evaluations to see queue activity
for i in {1..5}; do
  curl -X POST https://localhost/api/eval \
    -H "Content-Type: application/json" \
    -d "{\"code\": \"print('Test $i')\"}" \
    -k
done
```

### 4. Monitor Task Execution (Using API)
Since the web UI has limitations, use the API to monitor tasks:

```bash
# Get all tasks
curl -s -u admin:changeme http://localhost:5555/api/tasks | jq .

# Get task summary
curl -s -u admin:changeme http://localhost:5555/api/tasks | jq 'to_entries | map({
  task: .value.name,
  state: .value.state,
  time: .value.runtime
}) | group_by(.task) | map({
  task: .[0].task,
  count: length,
  states: group_by(.state) | map({state: .[0].state, count: length})
})'

# Watch task flow in real-time
watch -n 1 'curl -s -u admin:changeme http://localhost:5555/api/tasks | jq "length"'
```

### 5. Worker Information
Despite the 404 errors on some tabs, you can still see worker info:
- Worker name: `celery@<container-id>`
- Active tasks being processed
- Task completion rates

## Alternative Monitoring Methods

### 1. Command Line Monitoring
```bash
# Watch Celery worker logs
docker logs -f celery-worker-1

# Inspect worker stats directly
docker exec celery-worker-1 celery -A tasks inspect stats

# Check active tasks
docker exec celery-worker-1 celery -A tasks inspect active

# View task queue length
docker exec crucible-celery-redis redis-cli -n 0 llen celery
```

### 2. Redis Queue Inspection
```bash
# Connect to Redis
docker exec -it crucible-celery-redis redis-cli

# Select Celery database
SELECT 0

# List all keys
KEYS *

# Check queue length
LLEN celery

# View queue contents (be careful, this removes items!)
LRANGE celery 0 10
```

### 3. Custom Monitoring Script
```python
#!/usr/bin/env python3
import redis
import json
from datetime import datetime

# Connect to Redis
r = redis.Redis(host='localhost', port=6380, db=0)

# Get queue info
queue_length = r.llen('celery')
print(f"Queue Length: {queue_length}")

# Get recent task results
for key in r.keys('celery-task-meta-*')[:10]:
    result = json.loads(r.get(key))
    print(f"\nTask: {key.decode()}")
    print(f"Status: {result.get('status')}")
    print(f"Result: {result.get('result')}")
```

## Known Limitations

### Flower Dashboard Issues
1. **Worker/Broker 404 Errors**: The Flower version we're using (2.0) may have compatibility issues with our Celery setup
2. **Limited Worker Discovery**: Workers may not always appear in the dashboard
3. **Missing Metrics**: Some performance metrics aren't collected

### Workarounds
- Use command-line tools for detailed monitoring
- Check logs for real-time activity
- Consider upgrading to Celery 5.3+ with Flower 2.0+ for better compatibility

## Speaking Points for Demo

**When Flower Works Well:**
> "Here you can see our task queue monitoring dashboard. Notice how we can track every evaluation from submission through completion, with detailed timing information."

**When Encountering 404s:**
> "While some advanced features of Flower have compatibility issues with our current setup, the core task monitoring functionality works well. For detailed worker information, we can use command-line tools which provide even more granular data."

**On Monitoring Philosophy:**
> "In production, we'd integrate this with proper observability tools like Prometheus and Grafana for comprehensive metrics, alerts, and historical analysis."

## Integration Work Needed

### Immediate Fix (Tier 2 - ~1 hour)
To enable full Flower functionality:

1. **Use Custom Flower Image**:
   ```yaml
   # In docker-compose.yml, replace:
   image: mher/flower:2.0
   
   # With:
   build:
     context: .
     dockerfile: monitoring/flower/Dockerfile
   ```

2. **What This Enables**:
   - Worker discovery and status
   - Full task inspection with arguments/results
   - Proper queue depth monitoring
   - Task routing visualization

3. **Implementation**:
   - Custom Flower image already created in `/monitoring/flower/`
   - Includes our `tasks.py` module
   - Ready to integrate when needed

## Future Improvements

1. **Complete Flower Integration**: Use custom image (work already prepared)
2. **Add Prometheus Metrics**: Export Celery metrics for Grafana dashboards
3. **Custom Dashboard**: Build a purpose-fit monitoring UI for our specific needs
4. **Real-time WebSocket Updates**: Stream task status to the main UI

## Demo Tips

1. Have multiple terminal windows ready:
   - One for submitting evaluations
   - One for watching logs
   - One for Redis inspection

2. Pre-submit some evaluations before the demo to have data in Flower

3. If Flower isn't working well, pivot to command-line monitoring as "deeper debugging"

4. Emphasize that monitoring is critical for production systems