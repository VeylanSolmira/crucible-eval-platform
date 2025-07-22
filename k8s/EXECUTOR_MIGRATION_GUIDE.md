# Executor Migration Guide: From Docker Compose to Kubernetes

## Overview

This guide documents the phased approach to migrating executors from Docker Compose's static model to Kubernetes' dynamic scaling capabilities.

## Migration Phases

### Phase 1: Simple Mirror (Current Implementation) ✅
Mirror Docker Compose logic with minimal changes:
- Keep Docker proxy for container creation
- Use same executor logic and Redis registration
- Only change: executors use pod names instead of hardcoded IDs

### Phase 2: Kubernetes Jobs (Future)
Replace Docker containers with Kubernetes Jobs:
- Remove Docker proxy dependency
- Executors create K8s Jobs instead of Docker containers
- Better resource isolation and monitoring

### Phase 3: Advanced Patterns (Future)
Implement cloud-native patterns:
- Warm pools for fast startup
- Scale-to-zero for cost optimization
- Different executor types (GPU, high-memory, etc.)

## Current Architecture (Phase 1)

### Docker Compose Pattern
```
Celery Worker → Check Redis → Route to executor-1 or executor-2
                                        ↓
                            Docker Proxy → Create container
```

### Kubernetes Simple Pattern
```
Celery Worker → Check Redis → Route to any executor pod
                                        ↓
                            Docker Proxy → Create container
```

### What Changes
1. **Executor ID**: Uses pod name (e.g., `executor-abc123`) instead of `executor-1`
2. **Scaling**: Can have 2-10 executors via HPA instead of fixed 2-3
3. **Service Discovery**: Executors register with their pod IP

### What Stays the Same
- Docker proxy for container creation
- Redis for executor registration
- HTTP communication protocol
- Executor business logic

## Implementation Details

### Simple Executor Deployment
```yaml
# k8s/base/executors/executor-deployment-simple.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: executor
spec:
  replicas: 2  # Start like Docker Compose
  template:
    spec:
      containers:
      - name: executor
        env:
        - name: EXECUTOR_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name  # Dynamic pod name
```

### Code Changes Required
```python
# executor_service.py
import os

# OLD
executor_id = "executor-1"  # Hardcoded

# NEW
executor_id = os.environ.get('EXECUTOR_ID', 'executor-1')  # From pod name
```

### Redis Registration
```python
# Executor registers itself in Redis
redis_client.hset(
    "executors",
    executor_id,  # Now using pod name
    json.dumps({
        "url": f"http://{pod_ip}:8083",
        "status": "available",
        "max_concurrent": 1
    })
)
```

## Future: Removing Docker Proxy (Phase 2)

### Why Remove Docker Proxy?
1. **Security**: No Docker socket exposure
2. **Simplicity**: One less component
3. **Native K8s**: Better resource management
4. **Visibility**: All executions as K8s resources

### Migration Path
```python
# Add feature flag
USE_KUBERNETES_JOBS = os.environ.get('USE_K8S_JOBS', 'false') == 'true'

if USE_KUBERNETES_JOBS:
    create_kubernetes_job(eval_id, code)
else:
    create_docker_container(eval_id, code)  # Current method
```

### Required Changes
1. **RBAC**: Executors need permissions to create Jobs
2. **Client Library**: Add kubernetes-client to executor
3. **Job Templates**: Define Job specs for evaluations
4. **Monitoring**: Update to track Jobs instead of containers

## Future: Advanced Patterns (Phase 3)

### 1. Kubernetes Jobs Pattern
```yaml
# Direct job creation per evaluation
apiVersion: batch/v1
kind: Job
metadata:
  name: eval-{{eval_id}}
spec:
  ttlSecondsAfterFinished: 300
  template:
    spec:
      containers:
      - name: eval
        image: executor-ml:latest
        command: ["python", "-c", "{{code}}"]
```

### 2. Warm Pool Pattern
```yaml
# Pre-warmed executors for fast startup
apiVersion: apps/v1
kind: Deployment
metadata:
  name: executor-warm-pool
spec:
  replicas: 5  # Always ready
  template:
    spec:
      containers:
      - name: executor
        env:
        - name: MODE
          value: "warm-pool"
        - name: IDLE_TIMEOUT
          value: "300"  # Shutdown after 5 min idle
```

### 3. Hybrid Approach
```python
# Decision logic in Celery
def route_evaluation(eval_request):
    if eval_request.is_trusted and eval_request.expected_duration < 30:
        return use_warm_pool()  # Fast path
    else:
        return create_job()  # Isolated path
```

## Deployment Commands

### Current Deployment (Phase 1)
```bash
# Deploy with simple executors
kubectl apply -f k8s/base/executors/executor-deployment-simple.yaml

# Check executors
kubectl get pods -l app=executor

# Scale manually
kubectl scale deployment executor --replicas=5

# Enable autoscaling
kubectl apply -f k8s/base/executors/executor-hpa.yaml
```

### Testing Migration
```bash
# Test executor registration
kubectl exec -it deployment/executor -- python -c "
import redis
r = redis.Redis(host='redis')
print(r.hgetall('executors'))
"

# Watch scaling
kubectl get hpa executor-hpa -w
```

## Rollback Plan

If issues arise:
```bash
# Scale down to 2 (like Docker Compose)
kubectl scale deployment executor --replicas=2

# Or switch back to Docker Compose
docker-compose up -d executor-1 executor-2
kubectl scale deployment executor --replicas=0
```

## Benefits of Phased Approach

1. **Phase 1 Benefits**:
   - Minimal code changes
   - Can scale executors dynamically
   - Same debugging/monitoring tools
   - Easy rollback

2. **Phase 2 Benefits**:
   - Better security (no Docker socket)
   - Native Kubernetes resource management
   - Improved observability

3. **Phase 3 Benefits**:
   - Cost optimization (scale-to-zero)
   - Performance optimization (warm pools)
   - Support for different executor types

## Decision Criteria

### Stay with Phase 1 if:
- Current performance is acceptable
- Need quick migration to K8s
- Want minimal code changes
- Team familiar with Docker debugging

### Move to Phase 2 when:
- Security audit requires removing Docker socket
- Need better resource isolation
- Want unified K8s monitoring
- Ready for code changes

### Move to Phase 3 when:
- Cost optimization is critical
- Need < 1 second startup times
- Require different executor types
- Have K8s expertise on team

## Monitoring

### Current Metrics (Phase 1)
- Executor pod count
- Redis executor registration
- Docker container count per executor
- CPU/Memory per executor pod

### Future Metrics (Phase 2+)
- Job completion rate
- Job startup time
- Queue depth to executor ratio
- Cost per evaluation

## References

- [Kubernetes Job Documentation](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- [HPA Documentation](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Docker Socket Proxy Security](https://github.com/Tecnativa/docker-socket-proxy)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)