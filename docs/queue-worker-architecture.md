# Queue and Worker Architecture

## Overview

The Queue and Worker components form the asynchronous backbone of the evaluation platform, converting user requests into secure Kubernetes executions.

## Component Relationships

```
API Service → Queue → Worker → Kubernetes
                ↓        ↓
            (task)   (generates)
                      manifest
```

## Queue Component

### Purpose
- Decouple API from execution
- Handle burst traffic
- Enable retry/failure handling
- Provide system observability

### Technology Choice (Level 4)
- **Celery + Redis**: For MVP, Python-native solution
- **AWS SQS**: For production, managed service

### Message Format
```python
{
    "evaluation_id": "eval-123",
    "user_id": "user-456",
    "model_reference": "gpt-4",
    "script_location": "s3://scripts/eval-123.py",
    "resource_requirements": {
        "memory": "4Gi",
        "cpu": "2",
        "timeout_seconds": 3600
    },
    "safety_level": "high",
    "created_at": "2024-01-15T10:00:00Z"
}
```

## Worker Component (Orchestrator)

### Core Responsibilities

1. **Pull from Queue**
```python
@celery.task
def process_evaluation(evaluation_id):
    task = get_task_from_db(evaluation_id)
    manifest = generate_pod_manifest(task)
    pod = create_kubernetes_pod(manifest)
    monitor_pod_lifecycle(pod)
```

2. **Generate K8s Manifests Dynamically**
```python
def generate_pod_manifest(task):
    """
    Converts queue task into Kubernetes pod specification
    """
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": f"eval-{task.evaluation_id}",
            "labels": {
                "evaluation-id": task.evaluation_id,
                "user-id": task.user_id,
                "safety-level": task.safety_level
            }
        },
        "spec": {
            "securityContext": {
                "runAsNonRoot": True,
                "runAsUser": 1000
            },
            "containers": [{
                "name": "evaluator",
                "image": "metr/evaluator:latest",
                "resources": {
                    "limits": {
                        "memory": task.resource_requirements.memory,
                        "cpu": task.resource_requirements.cpu,
                        "ephemeral-storage": "10Gi"
                    }
                },
                "env": [
                    {"name": "EVALUATION_ID", "value": task.evaluation_id},
                    {"name": "MODEL_ID", "value": task.model_reference}
                ],
                "securityContext": {
                    "allowPrivilegeEscalation": False,
                    "readOnlyRootFilesystem": True
                }
            }],
            "restartPolicy": "Never",
            "activeDeadlineSeconds": task.resource_requirements.timeout_seconds
        }
    }
```

3. **Apply Security Policies Based on Safety Level**
```python
def apply_safety_constraints(manifest, safety_level):
    if safety_level == "high":
        # No network access
        manifest["spec"]["dnsPolicy"] = "None"
        # Stricter resource limits
        manifest["spec"]["containers"][0]["resources"]["limits"]["memory"] = "2Gi"
    elif safety_level == "medium":
        # Limited egress
        manifest["metadata"]["labels"]["network-policy"] = "restricted-egress"
    return manifest
```

4. **Monitor and React**
```python
async def monitor_pod_lifecycle(pod_name):
    while True:
        status = await k8s_client.read_pod_status(pod_name)
        
        if status.phase == "Failed":
            await handle_failure(pod_name)
            break
        elif status.phase == "Succeeded":
            await collect_results(pod_name)
            break
        elif await detect_safety_violation(pod_name):
            await emergency_stop(pod_name)
            break
            
        await asyncio.sleep(5)
```

## Why Dynamic Generation?

### 1. **Flexibility**
- Each evaluation has different requirements
- User-specified resource limits
- Variable safety levels

### 2. **Security**
- Generate unique names (no collisions)
- Apply appropriate isolation per evaluation
- Inject only necessary environment variables

### 3. **Scalability**
- No need to pre-create pod templates
- Can adapt to new evaluation types
- Easy to add new security policies

## Project Structure

```
metr-eval-platform/
├── src/
│   ├── api/           # API Service
│   ├── worker/        # Worker/Orchestrator ← Here
│   │   ├── __init__.py
│   │   ├── orchestrator.py    # Main worker logic
│   │   ├── k8s_client.py      # Kubernetes interactions
│   │   ├── manifest_builder.py # Dynamic manifest generation
│   │   ├── safety_monitor.py   # Safety violation detection
│   │   └── tasks.py           # Celery task definitions
│   └── common/        # Shared code
│       ├── models.py  # Data models
│       └── queue.py   # Queue abstractions
```

## Worker Deployment

The worker itself runs as:
```yaml
# k8s/worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: evaluation-worker
spec:
  replicas: 3  # Multiple workers for throughput
  selector:
    matchLabels:
      app: worker
  template:
    metadata:
      labels:
        app: worker
    spec:
      serviceAccountName: evaluation-worker  # Needs K8s API permissions
      containers:
      - name: worker
        image: metr/worker:latest
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
```

## Key Insights

1. **The Worker is a Kubernetes Controller** - It watches the queue and creates pods
2. **Manifests are Code** - Generated programmatically, not static YAML
3. **Safety is Dynamic** - Security policies applied based on evaluation risk
4. **State Management** - Worker tracks evaluation lifecycle in database

## Security Considerations

- Worker needs Kubernetes RBAC permissions to create/delete pods
- Should run in separate namespace from evaluations
- Audit log all pod creation/deletion
- Rate limit pod creation to prevent resource exhaustion

## Monitoring the Worker

```python
# Metrics to track
worker_metrics = {
    "evaluations_processed": Counter(),
    "pod_creation_time": Histogram(),
    "active_evaluations": Gauge(),
    "safety_violations": Counter()
}
```