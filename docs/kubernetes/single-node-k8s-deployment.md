# Single Node Kubernetes Deployment Guide

## Current Architecture

### What Gets Created

When you set `enable_k8s_single_node = true` and run Terraform:

```
AWS Infrastructure:
└── Single t2.micro EC2 instance
    └── K3s installed (lightweight Kubernetes)
        ├── Control Plane Components (in the same node!)
        │   ├── API Server
        │   ├── Scheduler
        │   ├── Controller Manager
        │   └── etcd (data store)
        └── Worker Components
            ├── kubelet
            ├── kube-proxy
            └── Container runtime (containerd)
            └── Your pods run here too!
```

### Important: Single Node Limitations

On our t2.micro (1 vCPU, 1 GB RAM):
- K3s itself uses ~500MB RAM
- Control plane uses ~200MB RAM
- **Available for your apps: ~300MB RAM** 😬

## Should We Use t3.micro Instead?

**YES!** Here's why:

| Instance | vCPUs | RAM | Cost/month | Available for Apps |
|----------|-------|-----|------------|-------------------|
| t2.micro | 1 | 1 GB | ~$8.50 | ~300 MB |
| t3.micro | 2 | 1 GB | ~$7.60 | ~300 MB |
| t3.small | 2 | 2 GB | ~$15.20 | ~1.3 GB ✓ |

**Recommendation: Use t3.small for Kubernetes**

Let me update our Terraform:

```hcl
# In k8s-single-node.tf
instance_type = "t3.small"  # Was t2.micro
```

## How Deployment Works

### Step 1: Infrastructure (Terraform)
```bash
# Creates the EC2 instance with K3s
terraform apply -var="enable_k8s_single_node=true"
```

### Step 2: Get Kubeconfig
```bash
# Download kubeconfig from the instance
scp ubuntu@<instance-ip>:~/.kube/config ./kubeconfig-crucible

# Use it locally
export KUBECONFIG=./kubeconfig-crucible
kubectl get nodes
```

### Step 3: Deploy Your Apps
```bash
# Apply your Kubernetes manifests
kubectl apply -f k8s/frontend/deployment.yaml
kubectl apply -f k8s/frontend/service.yaml
```

## What Happens on the Single Node

Everything runs on the same t3.small instance:

```yaml
# When you deploy the frontend:
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
spec:
  replicas: 2  # Both pods on same node!
```

The scheduler places both pods on the only available node:

```
t3.small Instance:
├── System & K3s (~700MB RAM)
├── frontend-pod-1 (256MB RAM)
├── frontend-pod-2 (256MB RAM)
└── Free: ~800MB RAM
```

## Single Node vs Multi-Node

### Current Single Node Setup
- **NO** ability to create new EC2 instances
- **NO** cluster autoscaler needed
- **NO** pod spreading across nodes
- All pods compete for same resources
- Node failure = complete outage

### Future Multi-Node Setup
Would require:
1. Multiple EC2 instances (created by Terraform)
2. Cluster autoscaler (creates EC2s dynamically)
3. Proper networking between nodes
4. Shared storage solution

## Deployment Workflow

### 1. Local Development (Current)
```bash
# Build locally
docker build -t crucible-platform/frontend:local ./frontend

# For single node K8s, you'd need to:
# Option A: Push to a registry
docker tag crucible-platform/frontend:local <registry>/frontend:v1
docker push <registry>/frontend:v1

# Option B: Save and load (manual)
docker save crucible-platform/frontend:local > frontend.tar
scp frontend.tar ubuntu@<node-ip>:~/
ssh ubuntu@<node-ip> "sudo k3s ctr images import frontend.tar"
```

### 2. CI/CD Deployment
```yaml
# .github/workflows/deploy-k8s.yml
steps:
  - name: Build and push to ECR
    run: |
      docker build -t $ECR_REPO/frontend:$SHA ./frontend
      docker push $ECR_REPO/frontend:$SHA
      
  - name: Deploy to K8s
    run: |
      kubectl set image deployment/frontend \
        frontend=$ECR_REPO/frontend:$SHA
```

## Resource Constraints Example

Here's what happens when you try to deploy too much on t2.micro:

```bash
$ kubectl get pods
NAME                    READY   STATUS    RESTARTS   AGE
frontend-abc123         1/1     Running   0          5m
frontend-def456         0/1     Pending   0          5m  # Can't fit!
api-ghi789             0/1     Pending   0          5m  # No resources!

$ kubectl describe pod frontend-def456
Events:
  Warning  FailedScheduling  pod/frontend-def456  
  0/1 nodes are available: 1 Insufficient memory.
```

## Proper Resource Management

### Set Resource Limits
```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: frontend
        resources:
          requests:
            memory: "128Mi"  # Minimum needed
            cpu: "100m"      # 0.1 CPU
          limits:
            memory: "256Mi"  # Maximum allowed
            cpu: "500m"      # 0.5 CPU
```

### Monitor Resources
```bash
# Check node capacity
kubectl describe node

# See actual usage
kubectl top node
kubectl top pods
```

## Single Node K8s Use Cases

### Good For:
- Learning Kubernetes concepts
- Testing manifests
- Development environments
- CI/CD preview environments

### NOT Good For:
- Production workloads
- High availability needs
- Multiple replicas for redundancy
- Resource-intensive workloads

## Migration Path

### Phase 1: Single Node (Current)
- Learn K8s concepts
- Test deployments
- Understand resource constraints

### Phase 2: Multi-Node (Fixed)
```hcl
# Create 3 node cluster
resource "aws_instance" "k8s_nodes" {
  count         = 3
  instance_type = "t3.small"
}
```

### Phase 3: Auto-scaling Cluster
- Add cluster autoscaler
- Dynamic node creation
- Production-ready

## Quick Commands

```bash
# Check what's running
kubectl get all -A

# See resource usage
kubectl top nodes
kubectl top pods

# Deploy frontend
kubectl apply -f k8s/frontend/

# Access frontend
kubectl port-forward svc/frontend-service 3000:3000

# Check logs
kubectl logs -f deployment/frontend

# SSH to debug
ssh ubuntu@<node-ip>
sudo k3s kubectl get pods  # On the node itself
```

## Important Notes

1. **Instance Type**: Change to t3.small minimum
2. **Control Plane**: Runs on same node (not separate)
3. **Scaling**: Can't scale beyond single node
4. **Deployment**: Need registry or manual image loading
5. **Resources**: Very limited, set proper limits