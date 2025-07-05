# Crucible Platform Demo Guide

## Quick Start

1. Start the platform:
   ```bash
   ./start-platform.sh
   ```

2. Open browser to http://localhost:3000

3. Run through the demo scenarios below

## Demo Scenarios

### 1. Basic Success Case
**Purpose**: Show normal operation
```python
print("Hello from Crucible!")
result = sum(range(100))
print(f"Sum of 0-99: {result}")
```
**Expected**: Completes in ~1 second, shows output

### 2. Concurrent Load Test
**Purpose**: Show platform handles multiple evaluations
- Click "Run 10 evaluations" button
- Watch the evaluations queue and process
- Open Flower dashboard (http://localhost:5555) to see Celery workers

### 3. Network Isolation
**Purpose**: Demonstrate security - code cannot access internet
- Copy code from `demo_scenarios.py` - "Network Isolation" section
- Submit and see all network attempts blocked

### 4. Timeout Handling
**Purpose**: Show graceful handling of infinite loops
```python
print("Starting infinite loop...")
while True:
    pass
```
**Expected**: Times out after 30 seconds, marked as failed

### 5. Error Handling
**Purpose**: Show various error types handled gracefully

**Syntax Error**:
```python
if True
    print("Missing colon!")
```

**Runtime Error**:
```python
x = 1 / 0  # Division by zero
```

### 6. Storage Explorer
**Purpose**: Show distributed storage capabilities
- Navigate to http://localhost:3000/storage
- Show evaluations stored in PostgreSQL
- Demonstrate search and filtering

### 7. Real-time Updates
**Purpose**: Show live status updates
- Submit a long-running evaluation
- Watch status change: queued → running → completed
- No page refresh needed

### 8. Resource Limits
**Purpose**: Show container resource isolation
- Use "Resource Limits" demo from `demo_scenarios.py`
- Shows memory limits enforced

## Demo Talk Track

### Opening (1 min)
"Crucible is a secure evaluation platform for running untrusted code. Think of it as a sandbox-as-a-service that could be used for AI model evaluation, code competitions, or educational platforms."

### Architecture (2 min)
"We use a microservices architecture with:
- FastAPI for the API layer
- Celery for distributed task processing
- Docker for secure code execution
- PostgreSQL for persistent storage
- Redis for caching and pub/sub
- React with TypeScript for the frontend"

### Security Demo (3 min)
"Security is paramount when running untrusted code. Let me show you our isolation:"
- Run network isolation test
- Run filesystem test
- Explain Docker security features

### Scale Demo (2 min)
"The platform scales horizontally:"
- Submit 10+ evaluations
- Show Flower dashboard with multiple workers
- Explain how we could add more executor nodes

### Monitoring (1 min)
"We have comprehensive monitoring:"
- Show Flower dashboard
- Show evaluation history
- Mention Prometheus/Grafana integration ready

### Closing (1 min)
"This demonstrates enterprise-grade platform engineering:
- Secure multi-tenant execution
- Horizontal scalability
- Production-ready monitoring
- Clean, maintainable architecture"

## Troubleshooting

### If services aren't starting:
```bash
docker-compose down -v
./start-platform.sh
```

### If evaluations stuck in "queued":
- Check Celery workers in Flower dashboard
- Restart workers: `docker-compose restart celery-worker`

### If getting 429 errors:
- Reduce number of concurrent submissions
- Wait a few seconds between batches

## Key Points to Emphasize

1. **Security First**: Network isolation, resource limits, file system restrictions
2. **Production Ready**: Health checks, monitoring, error handling
3. **Scalable Design**: Queue-based architecture, horizontal scaling
4. **Modern Stack**: React, TypeScript, FastAPI, Celery
5. **Developer Experience**: One-command startup, hot reloading, comprehensive docs