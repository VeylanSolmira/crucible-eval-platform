# Debug Resources

⚠️ **WARNING: These resources are for development/debugging only!**

This directory contains debugging utilities that should NEVER be deployed to production.

## debug-pod.yaml

A temporary pod for troubleshooting cluster issues.

### Usage

```bash
# Create debug pod
kubectl apply -f k8s/base/debug/debug-pod.yaml

# Connect to debug pod
kubectl exec -it debug-pod -n crucible -- /bin/bash

# Run Python tests or scripts
kubectl exec -it debug-pod -n crucible -- python -c "import requests; print(requests.get('http://api-service:8080/health').json())"

# Clean up
kubectl delete pod debug-pod -n crucible
```

### Features
- Auto-cleanup after 1 hour (activeDeadlineSeconds)
- Has test runner image with all dependencies
- Minimal security permissions
- Python environment configured

### Security Notes
- No service account (minimal permissions)
- Runs as non-root user
- No privilege escalation
- Resource limits enforced

### Common Debug Commands

```bash
# Test service connectivity
curl http://api-service:8080/health
curl http://celery-redis:6379

# Test Celery
python -c "from celery import Celery; app = Celery(); app.send_task('celery_worker.tasks.health_check')"

# Check Redis
redis-cli -h celery-redis ping
```