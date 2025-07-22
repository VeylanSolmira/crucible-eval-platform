# Local Development Memory Optimization

## Overview
This optimization reduces memory requests for local development from ~1.7GB to ~500MB, making it much easier to run the entire platform on Docker Desktop or similar local Kubernetes environments.

## Memory Reductions

| Service | Original Request | Optimized Request | Savings | Rationale |
|---------|-----------------|-------------------|---------|-----------|
| API | 128Mi | 64Mi | 64Mi | FastAPI starts small, grows as needed |
| Storage Service | 256Mi | 64Mi | 192Mi | Another lightweight FastAPI service |
| Storage Worker | 128Mi | 64Mi | 64Mi | Background worker with minimal base needs |
| Celery Worker | 256Mi | 128Mi | 128Mi | Needs more for task execution |
| Dispatcher | 128Mi | 64Mi | 64Mi | Simple K8s API client |
| PostgreSQL | 256Mi | 128Mi | 128Mi | DB needs decent memory for queries |
| Redis Main | 100Mi | 64Mi | 36Mi | Caching doesn't need much locally |
| Redis Celery | 200Mi | 64Mi | 136Mi | Task queue is light in dev |
| Frontend | 128Mi | 32Mi | 96Mi | Static nginx server |
| Flower | 128Mi | 64Mi | 64Mi | Monitoring UI |

**Total Savings: ~1.2GB**

## Important Notes

1. **Requests vs Limits**: We kept the original limits so services can burst when needed. The requests are what actually get reserved on the node.

2. **Why This Works for Dev**: 
   - No production load
   - Services start with minimal memory
   - Python's memory grows as needed
   - Kubernetes will allow bursting up to limits

3. **Production Warning**: These settings are ONLY for local development. Production should use the original settings or higher.

4. **Docker Desktop Settings**: With these optimizations, you should be able to run the platform comfortably with Docker Desktop set to 4GB RAM (leaving room for the OS and other containers).

## Monitoring Memory Usage

To see actual memory usage vs requests:

```bash
# See current usage
kubectl top pods -n crucible

# See requests and limits
kubectl describe nodes | grep -A 10 "Allocated resources"
```

## Reverting Changes

To use original memory settings, simply remove the patch from kustomization.yaml:

```yaml
# Remove this line:
- path: memory-optimization-patch.yaml
```