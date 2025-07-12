# Kubernetes on EC2: Architecture Overview

## The Two-Layer Architecture

### Layer 1: EC2 Instances (Nodes)
```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Account                              │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ EC2 Instance │  │ EC2 Instance │  │ EC2 Instance │         │
│  │ (Master)     │  │ (Worker)     │  │ (Worker)     │         │
│  │ t3.medium    │  │ t3.large     │  │ c5.2xlarge   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │ EC2 Instance │  │ EC2 Instance │  ← Can be added/removed    │
│  │ (Worker)     │  │ (Worker)     │    dynamically            │
│  │ t3.large     │  │ g4dn.xlarge  │                            │
│  └──────────────┘  └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

### Layer 2: Kubernetes Pods (Your Apps)
```
┌─────────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                            │
│                                                                  │
│  Node 1 (t3.large)          Node 2 (t3.large)                  │
│  ┌─────────────────┐        ┌─────────────────┐               │
│  │ frontend-pod-1  │        │ frontend-pod-2  │               │
│  │ api-pod-1       │        │ api-pod-2       │               │
│  │ redis-pod       │        │ postgres-pod    │               │
│  └─────────────────┘        └─────────────────┘               │
│                                                                  │
│  Node 3 (c5.2xlarge)        Node 4 (g4dn.xlarge)              │
│  ┌─────────────────┐        ┌─────────────────┐               │
│  │ executor-pod-1  │        │ executor-pod-2  │               │
│  │ executor-pod-2  │        │ (GPU workload)  │               │
│  │ executor-pod-3  │        │                 │               │
│  └─────────────────┘        └─────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

## Key Concepts

### 1. Control Plane (Master Nodes)
- Runs Kubernetes management components
- API server, scheduler, controller manager, etcd
- Usually 3 instances for HA
- Doesn't run your application pods

### 2. Worker Nodes
- EC2 instances where your pods actually run
- Each node runs:
  - kubelet (talks to control plane)
  - container runtime (Docker/containerd)
  - kube-proxy (networking)

### 3. Node Pools (Groups)
Different EC2 instance types for different workloads:

```yaml
# Example node pool configurations
nodeGroups:
  - name: general-purpose
    instanceType: t3.large
    minSize: 2
    maxSize: 10
    labels:
      workload-type: general
      
  - name: compute-optimized
    instanceType: c5.2xlarge
    minSize: 0  # Scale from zero!
    maxSize: 20
    taints:
      - key: workload-type
        value: executor
        effect: NoSchedule
    labels:
      workload-type: executor
      
  - name: gpu-nodes
    instanceType: g4dn.xlarge
    minSize: 0
    maxSize: 5
    taints:
      - key: nvidia.com/gpu
        value: "true"
        effect: NoSchedule
```

## How Dynamic Scaling Works

### 1. Horizontal Pod Autoscaler (HPA)
- Scales number of pods based on metrics
- "I need more executor pods because CPU is high"

### 2. Cluster Autoscaler
- Scales number of EC2 instances
- "I can't schedule these pods, need more nodes"
- Works with Auto Scaling Groups

### 3. The Flow
```
1. HPA sees high load → creates more executor pods
2. Scheduler can't find space → pods are "Pending"
3. Cluster Autoscaler sees pending pods
4. Launches new EC2 instance (takes 2-4 minutes)
5. New node joins cluster
6. Scheduler places pods on new node
```

## Your Specific Architecture

### Frontend & API
```yaml
# These run on general-purpose nodes
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
spec:
  replicas: 2
  template:
    spec:
      nodeSelector:
        workload-type: general
      containers:
      - name: frontend
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
```

### Executors (Dynamic)
```yaml
# These run on compute-optimized nodes
apiVersion: apps/v1
kind: Deployment
metadata:
  name: executor
spec:
  replicas: 0  # Start with zero
  template:
    spec:
      nodeSelector:
        workload-type: executor
      tolerations:
      - key: workload-type
        operator: Equal
        value: executor
        effect: NoSchedule
      containers:
      - name: executor
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
```

### HPA for Executors
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: executor-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: executor
  minReplicas: 0
  maxReplicas: 50
  metrics:
  - type: External
    external:
      metric:
        name: queue_length  # Scale based on job queue
      target:
        type: AverageValue
        averageValue: "2"  # 2 jobs per executor
```

## Infrastructure Provisioning Options

### Option 1: Pre-provisioned Node Pools
- Have minimum nodes always running
- Fast pod scheduling
- Higher baseline cost
- Good for predictable workloads

### Option 2: Scale from Zero
- Node pools start with 0 instances
- First pod triggers node creation (2-4 min delay)
- Very cost-effective
- Good for bursty workloads

### Option 3: Mixed Approach (Recommended)
```yaml
# Base capacity always on
general-purpose:
  minSize: 2
  maxSize: 10

# Executors scale from zero
executor-nodes:
  minSize: 0
  maxSize: 50
  
# GPU nodes only when needed
gpu-nodes:
  minSize: 0
  maxSize: 5
```

## Tools for Setup

### 1. Terraform
```hcl
# Creates the infrastructure
resource "aws_eks_cluster" "main" {
  name = "evaluation-platform"
  # ...
}

resource "aws_eks_node_group" "executors" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "executor-nodes"
  instance_types  = ["c5.2xlarge"]
  
  scaling_config {
    min_size     = 0
    max_size     = 50
    desired_size = 0
  }
}
```

### 2. eksctl (Alternative)
```yaml
# cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: evaluation-platform
  region: us-west-2

nodeGroups:
  - name: general
    instanceType: t3.large
    minSize: 2
    maxSize: 10
```

### 3. Cluster Autoscaler
Runs as a pod in your cluster, talks to AWS APIs to manage Auto Scaling Groups.

## Cost Optimization Strategies

1. **Spot Instances** for executors (70-90% cheaper)
2. **Scale to zero** for sporadic workloads
3. **Pod packing** - efficient resource requests
4. **Node termination handler** for graceful spot interruptions

## Timeline Example

```
T+0s:   User submits evaluation
T+1s:   API creates job in queue
T+2s:   HPA sees queue > threshold
T+3s:   HPA creates new executor pod
T+4s:   Pod is "Pending" (no space)
T+5s:   Cluster Autoscaler sees pending pod
T+6s:   Launches new EC2 instance
T+180s: EC2 instance ready, joins cluster
T+185s: Pod scheduled on new node
T+190s: Executor starts processing job
```

## Key Differences from Managed (EKS)

### Self-managed on EC2:
- You install Kubernetes yourself (kubeadm)
- You manage control plane updates
- You handle etcd backups
- More learning, more control
- Can use Spot instances for control plane

### EKS (for comparison):
- AWS manages control plane
- Automatic updates available
- Built-in etcd backups
- Less operational overhead
- Control plane costs ~$70/month

## Next Steps

1. Choose installation method (kubeadm vs k3s vs Rancher)
2. Design network architecture (VPC, subnets)
3. Set up Auto Scaling Groups
4. Install Cluster Autoscaler
5. Configure node pools with labels/taints
6. Test scale-from-zero behavior