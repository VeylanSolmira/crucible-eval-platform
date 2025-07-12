# Kubernetes Migration Guide: Docker Compose to K8s

## Table of Contents
1. [Migration Overview](#migration-overview)
2. [Architecture Decisions](#architecture-decisions)
3. [Resource Types Explained](#resource-types-explained)
4. [Service Communication](#service-communication)
5. [Storage and Persistence](#storage-and-persistence)
6. [Security Considerations](#security-considerations)
7. [Deployment Guide](#deployment-guide)
8. [Common Questions & Answers](#common-questions--answers)
9. [Troubleshooting](#troubleshooting)

## Migration Overview

This guide documents the migration from Docker Compose to Kubernetes for the Crucible Platform, a demonstration METR (Model Evaluation and Threat Research) system.

### What Was Migrated

| Docker Compose Service | Kubernetes Resource | Type | Purpose |
|------------------------|-------------------|------|----------|
| postgres | postgres-statefulset | StatefulSet | Database with persistent storage |
| redis | redis-main | Deployment | Event bus for platform |
| celery-redis | redis-celery | Deployment | Dedicated Redis for Celery tasks |
| api-service | api-service | Deployment | Main API service |
| storage-service | storage-service | Deployment | Storage API service |
| storage-worker | storage-worker | Deployment | Async storage worker |
| celery-worker | celery-worker | Deployment | Task queue processor |
| docker-proxy | docker-proxy | DaemonSet | Docker API proxy on each node |
| executor-1/2 | executor-1/2 | Deployment | Code execution sandboxes |
| flower | flower | Deployment | Celery monitoring dashboard |
| nginx | ingress | Ingress Controller | Reverse proxy and routing |
| crucible-frontend | frontend | Deployment | React frontend application |

## Architecture Decisions

### 1. Why StatefulSet for PostgreSQL?
**Decision**: Use StatefulSet instead of Deployment for PostgreSQL

**Reasons**:
- **Stable Network Identity**: Each pod gets a persistent hostname (postgres-0)
- **Ordered Deployment**: Pods are created/deleted in order
- **Persistent Storage**: Each pod gets its own PersistentVolumeClaim
- **Data Consistency**: Prevents split-brain scenarios in database replicas

**Alternative Considered**: Deployment with single replica
- **Why Not**: Deployments can accidentally create multiple pods during updates
- **When Better**: For stateless databases or when using external managed databases

### 2. Why DaemonSet for Docker Proxy?
**Decision**: Deploy docker-proxy as DaemonSet

**Reasons**:
- **Node-Local Access**: Each node needs its own Docker socket proxy
- **Automatic Scaling**: New nodes automatically get a proxy pod
- **Host Network**: Can use hostNetwork for better performance
- **Security Isolation**: Limits Docker socket access per node

**Alternative Considered**: Deployment with node affinity
- **Why Not**: Manual configuration for each node
- **When Better**: When you only need Docker access on specific nodes

### 3. Why Separate Redis Instances?
**Decision**: Deploy two Redis instances (main and celery)

**Reasons**:
- **Performance Isolation**: Celery tasks don't impact event bus
- **Different Configurations**: Task queue needs different memory policies
- **Failure Isolation**: One Redis failure doesn't affect both systems
- **Scaling Independence**: Can scale separately based on load

**Alternative Considered**: Single Redis with multiple databases
- **Why Not**: Shared memory and CPU limits
- **When Better**: For smaller deployments with resource constraints

## Resource Types Explained

### Deployments
Used for stateless applications that can be scaled horizontally:
- **api-service**: Multiple replicas for high availability
- **celery-worker**: Scale based on queue depth
- **storage-service**: Multiple replicas with shared storage

### StatefulSets
Used for stateful applications requiring stable identity:
- **postgres**: Database requiring persistent storage and stable network identity

### DaemonSets
Used for node-level services:
- **docker-proxy**: One instance per node for Docker API access

### Services
Kubernetes Services provide stable network endpoints:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
spec:
  clusterIP: None  # Headless service for StatefulSet
  selector:
    app: postgres
```

### ConfigMaps & Secrets
Separate configuration from code:
- **ConfigMaps**: Non-sensitive configuration
- **Secrets**: Passwords, API keys, certificates

## Service Communication

### DNS-Based Service Discovery
In Kubernetes, services communicate using DNS names:

| Docker Compose | Kubernetes | Full DNS Name |
|----------------|------------|---------------|
| postgres:5432 | postgres:5432 | postgres.crucible.svc.cluster.local |
| redis:6379 | redis:6379 | redis.crucible.svc.cluster.local |
| api-service:8080 | api-service:8080 | api-service.crucible.svc.cluster.local |

### Environment Variable Updates
```yaml
# Docker Compose
environment:
  - DATABASE_URL=postgresql://crucible:changeme@postgres:5432/crucible

# Kubernetes
env:
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: db-credentials
      key: database-url
```

## Storage and Persistence

### PersistentVolumeClaims (PVCs)
Different storage strategies for different needs:

1. **PostgreSQL** (StatefulSet):
   ```yaml
   volumeClaimTemplates:
   - metadata:
       name: postgres-storage
     spec:
       accessModes: ["ReadWriteOnce"]
       resources:
         requests:
           storage: 10Gi
   ```

2. **Shared Storage** (Multiple Pods):
   ```yaml
   volumes:
   - name: file-storage
     persistentVolumeClaim:
       claimName: storage-pvc  # ReadWriteMany
   ```

3. **Temporary Storage** (Pod-specific):
   ```yaml
   volumes:
   - name: tmp
     emptyDir:
       sizeLimit: 100Mi
   ```

### Storage Best Practices
- Use `ReadWriteOnce` for databases
- Use `ReadWriteMany` for shared file storage
- Use `emptyDir` for temporary/cache data
- Set resource limits on emptyDir volumes

## Security Considerations

### 1. Security Contexts
Every pod includes security hardening:
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop:
    - ALL
```

### 2. Network Policies
Control traffic between pods:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-policy
spec:
  podSelector:
    matchLabels:
      app: api-service
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nginx
```

### 3. Secrets Management
- Never commit real secrets to Git
- Use Kubernetes Secrets for sensitive data
- Consider using:
  - Sealed Secrets
  - External Secrets Operator
  - HashiCorp Vault

### 4. RBAC (Role-Based Access Control)
Control who can access resources:
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: crucible-reader
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list", "watch"]
```

## Deployment Guide

### Prerequisites
1. Kubernetes cluster (1.20+)
2. kubectl configured
3. Container images pushed to registry

### Step 1: Update Configuration
Replace placeholders in configuration files:
```bash
# Update secrets.yaml with real values
# Update ECR registry URLs in kustomization.yaml
export ECR_REGISTRY="123456789012.dkr.ecr.us-west-2.amazonaws.com"
export PROJECT_NAME="crucible-platform"
```

### Step 2: Deploy Base Resources
```bash
# Create namespace and base resources
kubectl apply -k k8s/base/

# Verify namespace creation
kubectl get namespace crucible

# Check all resources
kubectl get all -n crucible
```

### Step 3: Verify Deployment
```bash
# Check pod status
kubectl get pods -n crucible

# Check services
kubectl get svc -n crucible

# View logs
kubectl logs -n crucible deployment/api-service
```

### Step 4: Production Overlay (Optional)
```bash
# Apply production-specific changes
kubectl apply -k k8s/overlays/production/
```

## Common Questions & Answers

### Q: Why use Kubernetes instead of Docker Compose?
**A**: Kubernetes provides:
- **Production-grade orchestration**: Self-healing, rolling updates, scaling
- **Better resource management**: CPU/memory limits, autoscaling
- **Enhanced security**: Network policies, RBAC, security contexts
- **Cloud-native features**: Integration with cloud providers, load balancers
- **Declarative configuration**: GitOps-friendly

### Q: What's the purpose of namespace.yaml?
**A**: Namespaces provide:
- **Resource isolation**: Logical boundary for all application resources
- **Access control**: Apply RBAC policies at namespace level
- **Resource quotas**: Limit CPU/memory per namespace
- **Easy cleanup**: Delete entire namespace to remove all resources
- **Multi-tenancy**: Run multiple environments in same cluster

### Q: How do services find each other?
**A**: Kubernetes provides DNS-based service discovery:
- Short name: `postgres` (within same namespace)
- Full name: `postgres.crucible.svc.cluster.local`
- Services automatically get DNS entries
- No need for links or external service discovery

### Q: What happens to data in Kubernetes?
**A**: Data persistence depends on volume type:
- **PersistentVolumeClaim**: Data survives pod restarts
- **emptyDir**: Data deleted when pod is removed
- **hostPath**: Data stored on node (not recommended)
- **ConfigMap/Secret**: Configuration data managed by Kubernetes

### Q: How is security improved?
**A**: Multiple security layers:
- **Pod Security**: Non-root users, read-only filesystems
- **Network Policies**: Control inter-pod communication
- **RBAC**: Fine-grained access control
- **Secrets Management**: Encrypted at rest
- **Security Contexts**: Capability dropping, privilege escalation prevention

### Q: Can I use Helm instead?
**A**: Yes! Benefits of Helm:
- **Templating**: Reuse charts across environments
- **Package Management**: Easy install/upgrade/rollback
- **Values Files**: Environment-specific configuration
- **Dependencies**: Manage chart dependencies

Convert to Helm:
```bash
helm create crucible-platform
# Move manifests to templates/
# Create values.yaml for configuration
```

### Q: How do I handle database migrations?
**A**: Use Kubernetes Jobs:
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: migrate
        image: ${ECR_REGISTRY}/storage-service:latest
        command: ["alembic", "upgrade", "head"]
```

### Q: What about logging and monitoring?
**A**: Standard Kubernetes patterns:
- **Logging**: Use fluentd/fluent-bit to collect logs
- **Monitoring**: Prometheus for metrics, Grafana for visualization
- **Tracing**: Jaeger or similar for distributed tracing
- **Service Mesh**: Istio/Linkerd for advanced observability

## Troubleshooting

### Pod Won't Start
```bash
# Check pod status
kubectl describe pod <pod-name> -n crucible

# Common issues:
# - ImagePullBackOff: Wrong image name or no registry access
# - CrashLoopBackOff: Application crashing on startup
# - Pending: Insufficient resources or PVC not bound
```

### Service Not Accessible
```bash
# Check service endpoints
kubectl get endpoints -n crucible

# Test service DNS
kubectl run -it --rm debug --image=busybox --restart=Never -n crucible -- nslookup api-service
```

### Database Connection Issues
```bash
# Check if postgres is running
kubectl get pod -n crucible -l app=postgres

# Test connection
kubectl run -it --rm psql --image=postgres:15-alpine --restart=Never -n crucible -- psql -h postgres -U crucible -d crucible
```

### Storage Issues
```bash
# Check PVC status
kubectl get pvc -n crucible

# Check PV binding
kubectl describe pvc <pvc-name> -n crucible
```

## Best Practices

1. **Resource Limits**: Always set requests and limits
2. **Health Checks**: Configure liveness and readiness probes
3. **Labels**: Use consistent labeling strategy
4. **Secrets**: Never hardcode secrets in manifests
5. **Monitoring**: Set up monitoring before production
6. **Backup**: Regular database backups
7. **Updates**: Use rolling update strategy
8. **Documentation**: Keep docs in sync with changes

## Next Steps

1. **Set up CI/CD**: Automate deployments with GitOps
2. **Add Monitoring**: Deploy Prometheus and Grafana
3. **Implement Autoscaling**: HPA for dynamic scaling
4. **Security Scanning**: Add image scanning to pipeline
5. **Disaster Recovery**: Test backup and restore procedures
6. **Load Testing**: Validate scaling under load

## References

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [12 Factor App](https://12factor.net/)
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/)
- [Kustomize Documentation](https://kustomize.io/)