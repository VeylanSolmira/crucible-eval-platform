# Container Orchestration: Docker Compose vs Kubernetes

## The Dynamic Scaling Challenge

Our platform has two very different scaling needs:
- **Frontend**: Maybe 2-10 instances based on user traffic
- **Executors**: Could need 0-1000 based on evaluation load

## Docker Compose: Static Orchestration

### What It Can Do
```yaml
services:
  platform:
    image: crucible:platform
    deploy:
      replicas: 3  # Fixed number
```

### What It CAN'T Do
- Create containers dynamically
- Scale based on workload
- Create a new container per job
- Auto-cleanup completed jobs

### Workarounds
1. **Pre-created Pool**: Define executor-1 through executor-10
2. **External Scripts**: Use docker-compose + bash scripts
3. **Docker-in-Docker**: Security nightmare

## Kubernetes: Dynamic Orchestration

### The Job Pattern
```yaml
# Template for dynamic job creation
apiVersion: batch/v1
kind: Job
metadata:
  name: execution-${EVAL_ID}  # Unique per execution
spec:
  template:
    spec:
      containers:
      - name: executor
        image: python:3.11-slim
```

### How Kubernetes Solves It
1. **API-Driven**: Create jobs programmatically
2. **Dynamic Scaling**: 0 to 1000s of pods
3. **Resource Management**: CPU/memory limits enforced
4. **Automatic Cleanup**: Jobs self-destruct

### Under the Hood
- **Kubelet** has privileged access to container runtime
- Users interact with Kubernetes API, not Docker
- RBAC controls who can create what
- No direct container runtime access needed

## Translation: Compose → Kubernetes

### Tools
- **Kompose**: Most popular converter
- **docker compose convert**: Built-in (experimental)

### What Translates Well
- Basic services → Deployments
- Ports → Services
- Environment variables → ConfigMaps
- Networks → Automatic in K8s

### What Needs Rethinking
- Volume mounts → PersistentVolumeClaims
- docker.sock mounts → Different pattern entirely
- depends_on → Init containers or readiness probes
- Privileged mode → SecurityContext

## The Reality for Development

Docker Compose is perfect for:
- Local development
- Simple deployments
- Static service architectures

But when you need:
- Dynamic job creation
- Different scaling per service
- Resource isolation per task
- Production-grade orchestration

...that's when teams move to Kubernetes.

## Pragmatic Approach

1. **Start with Docker Compose** (simple, works locally)
2. **Document limitations** ("In production, would use K8s Jobs")
3. **Include K8s manifests** (show you understand the upgrade path)
4. **Focus on core functionality** (not orchestration complexity)