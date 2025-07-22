# Dispatcher Architecture Decision: From Docker Proxy to Kubernetes Jobs

## Executive Summary

After analyzing the migration from Docker-based executors to Kubernetes Jobs, we recommend implementing a **stateless dispatcher service** as a separate microservice rather than embedding K8s logic directly in Celery workers or using a sidecar pattern.

## Context

The METR evaluation platform is migrating from Docker Compose to Kubernetes. The current architecture uses:
- Docker proxy for container creation
- Static executor services (executor-1, executor-2)
- Celery workers that route to executors

The question: Should we eliminate executors entirely and have Celery create K8s Jobs directly?

## Architecture Options Analyzed

### Option 1: Direct Integration (Celery → K8s Jobs)
```
API → Celery Worker → K8s API → Job Pod
```

### Option 2: Stateless Dispatcher Service
```
API → Celery Worker → Dispatcher Service → K8s API → Job Pod
```

### Option 3: Sidecar Pattern
```
Pod: [Celery Worker Container + Dispatcher Sidecar] → K8s API → Job Pod
```

## Deep Analysis

### 1. Coupling & Flexibility

**Direct Integration:**
- ❌ Celery tightly coupled to K8s
- ❌ Switching to AWS SQS = rewrite Celery worker
- ❌ Switching to AWS Batch = rewrite Celery worker
- ❌ Testing requires K8s or extensive mocking

**Dispatcher Service:**
- ✅ Celery only knows HTTP
- ✅ Switching to SQS = only change API layer
- ✅ Switching to AWS Batch = only change dispatcher
- ✅ Testing with simple HTTP mocks

### 2. Security Considerations

**Direct Integration:**
```yaml
┌─────────────────┐
│  Celery Worker  │ ← Has K8s RBAC permissions
│  (processes all │ ← If compromised, can create any Job
│   queue tasks)  │
└─────────────────┘
```

**Dispatcher Service:**
```yaml
┌─────────────────┐     ┌─────────────────┐
│  Celery Worker  │     │   Dispatcher    │
│  (no K8s RBAC)  │────▶│ (K8s RBAC only) │ ← Isolated
└─────────────────┘     └─────────────────┘
                              │
                              ▼
                        ┌──────────┐
                        │ K8s Job  │ ← Double isolated
                        └──────────┘
```

### 3. Evolution & Migration Scenarios

**Scenario 1: Multi-Cloud Migration**
- Company wants to run on both AWS EKS and GCP GKE
- **Direct**: Modify every Celery worker
- **Dispatcher**: Add cloud routing to dispatcher

**Scenario 2: Add GPU Support**
- Some evaluations need GPUs
- **Direct**: Add logic to all Celery workers
- **Dispatcher**: Update dispatcher to set GPU resources

**Scenario 3: Replace Celery with AWS SQS**
- Company standardizes on AWS
- **Direct**: Rewrite all execution logic
- **Dispatcher**: Just change queue layer

### 4. Queue Heterogeneity

Future Celery tasks might include:
```python
- evaluate_code()      # Needs dispatcher
- generate_report()    # Doesn't need dispatcher
- cleanup_storage()    # Doesn't need dispatcher
- notify_user()        # Doesn't need dispatcher
```

With direct integration, all workers need K8s permissions even for tasks that don't create Jobs.

## Sidecar vs Separate Service Analysis

### Decision Matrix

| Factor | Sidecar | Separate Service | **Winner** |
|--------|---------|------------------|------------|
| **Security Isolation** | Same pod, shared fate | Network boundary | **Separate** ✅ |
| **Queue Flexibility** | Must deploy together | Can scale independently | **Separate** ✅ |
| **Operational Simplicity** | One deployment | Two deployments | **Sidecar** |
| **Evolution/Updates** | Update both together | Update independently | **Separate** ✅ |
| **Resource Efficiency** | Dispatcher per worker | Shared dispatchers | **Separate** ✅ |
| **Network Reliability** | Can't fail (localhost) | Could fail (rare) | **Sidecar** |
| **Latency** | ~1ms (localhost) | ~50ms (network) | **Sidecar** |

### Key Considerations for METR

1. **Security is Paramount**: METR deals with potentially adversarial code
2. **Queue Diversity**: Not all tasks need K8s Job creation
3. **Evolution Path**: Need to iterate on dispatcher without touching queue layer
4. **Resource Efficiency**: 10 workers don't need 10 dispatchers

## Recommendation: Stateless Dispatcher Service

### Architecture
```yaml
┌─────────────────┐
│   API Service   │
└────────┬────────┘
         │ Enqueue
┌────────▼────────┐
│     Celery      │ (Just queuing, no K8s knowledge)
│    Workers      │ 
└────────┬────────┘
         │ HTTP POST /execute
┌────────▼────────┐
│   Dispatcher    │ (Stateless, K8s Job creator)
│    Service      │ (2-3 replicas for HA)
└────────┬────────┘
         │ Creates
┌────────▼────────┐
│   K8s Job       │ (Actual evaluation)
│  (executor-ml)  │
└─────────────────┘
```

### Benefits

1. **Future-Proof**: Easy to switch queue systems or execution backends
2. **Secure**: Each component has minimal permissions (principle of least privilege)
3. **Testable**: Simple HTTP interface
4. **Focused**: Each component has one job
5. **Evolvable**: Can add features without touching queue layer
6. **Standard**: Common microservices pattern

### Implementation Example

```python
# dispatcher/app.py
from fastapi import FastAPI, HTTPException
from kubernetes import client, config
import os

app = FastAPI()

# Load K8s config
try:
    config.load_incluster_config()
except:
    config.load_kube_config()

batch_v1 = client.BatchV1Api()
namespace = os.getenv("KUBERNETES_NAMESPACE", "crucible")

@app.post("/execute")
async def execute(eval_id: str, code: str, timeout: int = 300):
    """Create a K8s Job for code evaluation."""
    
    job = client.V1Job(
        metadata=client.V1ObjectMeta(
            name=f"eval-{eval_id}",
            labels={"eval-id": eval_id}
        ),
        spec=client.V1JobSpec(
            ttl_seconds_after_finished=300,
            active_deadline_seconds=timeout,
            template=client.V1PodTemplateSpec(
                spec=client.V1PodSpec(
                    restart_policy="Never",
                    containers=[
                        client.V1Container(
                            name="eval",
                            image="executor-ml:latest",
                            command=["python", "-c", code],
                            resources=client.V1ResourceRequirements(
                                limits={"memory": "512Mi", "cpu": "0.5"},
                                requests={"memory": "256Mi", "cpu": "0.25"}
                            )
                        )
                    ]
                )
            )
        )
    )
    
    try:
        batch_v1.create_namespaced_job(namespace, job)
        return {"eval_id": eval_id, "status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Implementation Path

### Phase 1: Basic Dispatcher (Week 1)
- Create simple FastAPI service
- Implement /execute endpoint
- Basic K8s Job creation
- Deploy with 2 replicas

### Phase 2: Production Features (Week 2-3)
- Add health checks and readiness probes
- Implement proper error handling
- Add structured logging
- Create Prometheus metrics

### Phase 3: Advanced Features (Month 2+)
- Circuit breaker for K8s API
- Request queuing/batching
- GPU support
- Multi-cluster routing
- Cost controls

## Migration Strategy

1. **Deploy dispatcher alongside existing executors**
2. **Update Celery to use dispatcher for percentage of traffic**
3. **Monitor and compare performance**
4. **Gradually increase traffic to dispatcher**
5. **Remove executor services once stable**

## Monitoring & Observability

Key metrics to track:
- Dispatcher request latency
- K8s Job creation success rate
- Job completion times
- Resource utilization
- Error rates by type

## Security Considerations

1. **Network Policies**: Restrict dispatcher to only accept from Celery
2. **RBAC**: Minimal permissions (create/get/list Jobs in specific namespace)
3. **Pod Security**: Run as non-root, read-only filesystem
4. **Audit Logging**: Track all Job creation requests

## Conclusion

The stateless dispatcher service provides the best balance of:
- **Security**: Proper isolation boundaries
- **Flexibility**: Easy to evolve and migrate
- **Simplicity**: Clear separation of concerns
- **Performance**: Negligible overhead vs significant benefits

This architecture positions METR to easily adapt to future requirements while maintaining security and operational simplicity.