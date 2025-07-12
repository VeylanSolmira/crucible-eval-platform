# Kubernetes Migration Guide

## Overview

This guide documents the incremental migration from Docker Compose to Kubernetes, designed as a learning journey. We start with a single service and gradually add complexity, ensuring deep understanding at each step.

## Migration Philosophy

Rather than a "big bang" migration, we're taking an incremental approach:
1. **Learn by Building** - Understand each K8s concept through hands-on implementation
2. **Start Simple** - Begin with stateless services, add complexity gradually
3. **Local First** - Master concepts locally before cloud deployment
4. **Document Everything** - Capture learnings and gotchas for future reference

## Phase 1: Frontend Service (Learning K8s Basics)

### Why Start with Frontend?
- **Stateless** - No persistent storage complexity
- **Single Container** - Simple deployment model
- **Clear Success** - Visual confirmation when working
- **Minimal Dependencies** - Can run standalone

### Prerequisites
- Install kind (via Docker Desktop on macOS)
- Install kubectl
- Docker Desktop (for local image building)

### Create Single-Node Cluster

We'll start with a single-node cluster using Kubernetes 1.32.5:

```bash
# Create single-node cluster with specific version
kind create cluster --name crucible-learn --image kindest/node:v1.32.5

# Verify cluster is running
kubectl cluster-info --context kind-crucible-learn

# Check the node
kubectl get nodes
# Should show one node with roles: control-plane,master
```

### Step 1: Create Frontend Deployment

```yaml
# kubernetes/frontend/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crucible-frontend
  labels:
    app: crucible
    component: frontend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: crucible
      component: frontend
  template:
    metadata:
      labels:
        app: crucible
        component: frontend
    spec:
      containers:
      - name: frontend
        image: crucible-platform/frontend:local
        imagePullPolicy: Never  # For local development
        ports:
        - containerPort: 3000
        env:
        - name: NODE_ENV
          value: "production"
        - name: NEXT_PUBLIC_API_URL
          value: "http://api-service:8080"  # Will add later
        livenessProbe:
          httpGet:
            path: /
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Step 2: Create Frontend Service

```yaml
# kubernetes/frontend/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: crucible-frontend
  labels:
    app: crucible
    component: frontend
spec:
  type: NodePort  # For local access
  ports:
  - port: 3000
    targetPort: 3000
    nodePort: 30000  # Access at localhost:30000
  selector:
    app: crucible
    component: frontend
```

### Step 3: Deploy and Test

```bash
# Build image locally
docker build -t crucible-platform/frontend:local ./frontend

# Load image into kind
kind load docker-image crucible-platform/frontend:local --name crucible-learn

# Apply configurations
kubectl apply -f k8s/frontend/

# Check status
kubectl get pods
kubectl get services

# Access the frontend (since we're using NodePort)
# First, get the node's IP (in kind, it's typically localhost)
kubectl port-forward service/crucible-frontend 3000:3000

# Now access at http://localhost:3000
```

### Learning Checkpoints
- [ ] Understand Deployment vs Pod
- [ ] Understand Service types (ClusterIP, NodePort, LoadBalancer)
- [ ] Understand Labels and Selectors
- [ ] Understand Probes (liveness vs readiness)
- [ ] Practice kubectl commands (logs, describe, exec)

## Phase 2: Add API Service (Inter-Service Communication)

### New Concepts
- Service discovery
- Environment configuration
- Multi-container coordination

### Step 1: Create API Deployment

```yaml
# kubernetes/api/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-service
  labels:
    app: crucible
    component: api
spec:
  replicas: 1
  selector:
    matchLabels:
      app: crucible
      component: api
  template:
    metadata:
      labels:
        app: crucible
        component: api
    spec:
      containers:
      - name: api
        image: crucible-platform/api-service:local
        ports:
        - containerPort: 8080
        env:
        - name: STORAGE_SERVICE_URL
          value: "http://storage-service:8082"  # Will add later
        - name: REDIS_HOST
          value: "redis"  # Will add later
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
```

### Step 2: Create API Service

```yaml
# kubernetes/api/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: api-service
spec:
  ports:
  - port: 8080
    targetPort: 8080
  selector:
    app: crucible
    component: api
```

### Step 3: Update Frontend to Connect

Now the frontend can reach the API at `http://api-service:8080` through Kubernetes DNS!

### Learning Checkpoints
- [ ] Understand Kubernetes DNS (service.namespace.svc.cluster.local)
- [ ] Understand ClusterIP services
- [ ] Debug inter-service communication
- [ ] Use kubectl port-forward for debugging

## Phase 3: Add Stateful Services (Storage & Redis)

### New Concepts
- ConfigMaps for configuration
- Secrets for sensitive data
- PersistentVolumes for storage
- StatefulSets vs Deployments

### Step 1: Create ConfigMap

```yaml
# kubernetes/config/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: crucible-config
data:
  database_host: "postgres"
  database_name: "crucible"
  redis_host: "redis"
  storage_backend: "database"
```

### Step 2: Create Secrets

```yaml
# kubernetes/config/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: crucible-secrets
type: Opaque
stringData:
  database_password: "crucible_password"
  internal_api_key: "dev_internal_key_123"
```

### Learning Checkpoints
- [ ] Understand ConfigMaps vs Secrets
- [ ] Learn about PersistentVolumes and Claims
- [ ] Understand StatefulSets for databases
- [ ] Practice volume mounting

## Phase 4: Complete Migration (All Services)

### Service Migration Order
1. ✅ Frontend (stateless, simple)
2. ✅ API Gateway (stateless, service discovery)
3. Storage Service (database connection)
4. Redis (stateful, persistence)
5. PostgreSQL (stateful, critical data)
6. Celery Workers (background jobs)
7. Executors (Docker-in-Docker complexity)
8. Nginx (Ingress controller)

### Complex Services Considerations

#### Executors (Hardest)
- Need Docker socket access
- Security implications
- Consider Kata containers or gVisor
- May need privileged mode initially

#### Celery Workers
- Need Redis connection
- Scaling considerations
- Job queue management

#### PostgreSQL
- Data persistence critical
- Backup strategy needed
- Consider cloud-managed option

## Phase 5: Multi-Node Deployment

Once comfortable with single-node, expand to multi-node:

### Create Multi-Node Cluster
```yaml
# kind-multi-node.yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  image: kindest/node:v1.32.5
- role: worker
  image: kindest/node:v1.32.5
- role: worker
  image: kindest/node:v1.32.5
```

```bash
# Delete single-node cluster
kind delete cluster --name crucible-learn

# Create multi-node cluster
kind create cluster --name crucible-multi --config kind-multi-node.yaml

# See your nodes
kubectl get nodes
```

### EC2 Deployment Options
1. **EKS** - Managed Kubernetes (easier, more expensive)
2. **Kops** - Self-managed on EC2 (more control, more work)
3. **Kubeadm** - Manual setup (maximum learning, maximum effort)

### Multi-Node Considerations
- Node affinity/anti-affinity
- Network policies
- Storage classes
- Load balancing

## Common Pitfalls & Solutions

### Image Pull Issues
- **Problem**: ImagePullBackOff errors
- **Solution**: Ensure images are accessible (ECR, Docker Hub, or loaded locally)

### Service Discovery Failures
- **Problem**: Services can't find each other
- **Solution**: Check service names, namespaces, and DNS

### Permission Errors
- **Problem**: Pods can't access resources
- **Solution**: Check ServiceAccounts and RBAC

### Storage Issues
- **Problem**: Pods can't mount volumes
- **Solution**: Verify PV/PVC binding and storage classes

## Learning Resources

### Essential Concepts
1. [Kubernetes Basics](https://kubernetes.io/docs/tutorials/kubernetes-basics/)
2. [Networking Model](https://kubernetes.io/docs/concepts/services-networking/)
3. [Storage](https://kubernetes.io/docs/concepts/storage/)
4. [Security](https://kubernetes.io/docs/concepts/security/)

### Hands-On Practice
- [Katacoda K8s Scenarios](https://www.katacoda.com/courses/kubernetes)
- [Play with Kubernetes](https://labs.play-with-k8s.com/)

### Debugging Tools
- `kubectl logs`
- `kubectl describe`
- `kubectl exec`
- `kubectl port-forward`
- K9s (terminal UI)

## Success Metrics

### Phase 1 Success
- [ ] Frontend accessible via browser
- [ ] Can modify and redeploy
- [ ] Understand basic K8s objects

### Phase 2 Success
- [ ] Frontend can call API
- [ ] Both services running stable
- [ ] Can debug networking issues

### Full Migration Success
- [ ] All services running in K8s
- [ ] Data persistence working
- [ ] Can scale services
- [ ] Monitoring operational

## Next Steps

After completing local migration:
1. Add monitoring (Prometheus/Grafana)
2. Implement proper ingress
3. Add autoscaling
4. Security hardening
5. CI/CD integration

Remember: **Every error is a learning opportunity!**