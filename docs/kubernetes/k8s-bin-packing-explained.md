# Kubernetes as a Bin Packing Problem

## The Mental Model

```
Bins = EC2 Instances (Nodes)
Items = Pods
Item Size = CPU + Memory requests
Bin Size = EC2 instance capacity

When bins get full → Create new bins (launch EC2s)
When bins get empty → Remove bins (terminate EC2s)
```

## Visual Example

```
Node 1 (t3.large: 2 CPU, 8GB RAM)
┌─────────────────────────────────┐
│ Available: 2 CPU, 8GB           │
│                                 │
│ kubelet+OS: 0.2 CPU, 0.5GB     │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│                                 │
│ frontend-pod: 0.5 CPU, 1GB     │
│ ███████████████████████████████ │
│                                 │
│ api-pod: 1 CPU, 2GB            │
│ ███████████████████████████████ │
│ ███████████████████████████████ │
│                                 │
│ Remaining: 0.3 CPU, 4.5GB      │
│ (Too small for executor!)       │
└─────────────────────────────────┘

New executor needs: 2 CPU, 4GB
Won't fit! → Cluster Autoscaler creates new node
```

## The Scheduling Algorithm

```python
# Simplified version of what Kubernetes does
def schedule_pod(pod, nodes):
    # 1. Filter nodes that CAN run this pod
    eligible_nodes = []
    for node in nodes:
        if (node.available_cpu >= pod.requested_cpu and
            node.available_memory >= pod.requested_memory and
            matches_node_selector(pod, node) and
            tolerates_taints(pod, node)):
            eligible_nodes.append(node)
    
    # 2. Score nodes (which is BEST?)
    scored_nodes = []
    for node in eligible_nodes:
        score = 0
        # Prefer nodes with more free resources after scheduling
        score += resource_balance_score(node, pod)
        # Prefer nodes already running similar pods
        score += affinity_score(node, pod)
        # Avoid nodes with anti-affinity pods
        score -= anti_affinity_penalty(node, pod)
        scored_nodes.append((node, score))
    
    # 3. Pick best node
    best_node = max(scored_nodes, key=lambda x: x[1])
    return best_node

# If no nodes available → Pod stays "Pending"
# Cluster Autoscaler sees Pending → Creates new node
```

## Real Configuration Example

### 1. Control Plane (Usually Separate)
```yaml
# EKS handles this for you, but in self-managed:
apiVersion: v1
kind: Node
metadata:
  labels:
    node-role.kubernetes.io/control-plane: ""
spec:
  taints:
  - effect: NoSchedule
    key: node-role.kubernetes.io/control-plane
  # This ensures ONLY control plane pods run here
```

### 2. Node Resource Allocation
```yaml
# What actually happens on a t3.large (2 CPU, 8GB RAM):
Total Resources:      2000m CPU, 8192MB RAM
Reserved by kubelet:  200m CPU, 512MB RAM  # System overhead
Reserved by OS:       100m CPU, 256MB RAM   # Linux needs some
Available to pods:    1700m CPU, 7424MB RAM # What you can actually use
```

### 3. Pod Fitting Rules
```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: app
    resources:
      requests:        # Minimum needed (for scheduling)
        memory: "1Gi"
        cpu: "500m"
      limits:          # Maximum allowed (for cgroups)
        memory: "2Gi"
        cpu: "1000m"
```

## Autoscaling Triggers

### Cluster Autoscaler Decision Tree
```
Every 10 seconds:
├─ Are there Pending pods?
│  ├─ Yes → Can any node groups accommodate them?
│  │  ├─ Yes → Launch new instances
│  │  └─ No → Log "unable to scale"
│  └─ No → Continue
│
├─ Are there underutilized nodes?
│  ├─ Yes → Can pods be moved elsewhere?
│  │  ├─ Yes → Mark node for termination
│  │  └─ No → Keep node
│  └─ No → Continue
```

### Configuration Example
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-autoscaler-config
data:
  nodes.max: "50"
  nodes.min: "0"
  scale-down-utilization-threshold: "0.5"  # If node < 50% utilized
  scale-down-delay-after-add: "10m"        # Wait after adding node
  scale-down-unneeded-time: "10m"          # Node empty for 10m
  expander: "least-waste"                   # Pick smallest instance that fits
```

## Advanced Packing Strategies

### 1. Node Groups by Workload Type
```hcl
# Terraform example
locals {
  node_groups = {
    # Small, general purpose
    general = {
      instance_types = ["t3.medium", "t3.large"]
      min_size = 2  # Always have some capacity
      max_size = 10
      labels = {
        workload = "general"
      }
    }
    
    # Large, compute intensive
    compute = {
      instance_types = ["c5.2xlarge", "c5.4xlarge"]
      min_size = 0  # Scale from zero
      max_size = 20
      labels = {
        workload = "compute"
      }
      taints = [{
        key    = "workload"
        value  = "compute"
        effect = "NoSchedule"
      }]
    }
    
    # GPU instances
    gpu = {
      instance_types = ["g4dn.xlarge"]
      min_size = 0
      max_size = 5
      labels = {
        workload = "gpu"
        "nvidia.com/gpu" = "true"
      }
      taints = [{
        key    = "nvidia.com/gpu"
        value  = "true"
        effect = "NoSchedule"
      }]
    }
  }
}
```

### 2. Pod Placement Control
```yaml
# Force specific node types
apiVersion: batch/v1
kind: Job
spec:
  template:
    spec:
      # Must go on GPU node
      nodeSelector:
        nvidia.com/gpu: "true"
      
      # Tolerate GPU taint
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        
      # Prefer nodes with least utilization
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: node.kubernetes.io/utilization
                operator: Lt
                values: ["50"]
```

### 3. Bin Packing Efficiency
```yaml
# Configure scheduler to pack efficiently
apiVersion: v1
kind: ConfigMap
metadata:
  name: scheduler-config
data:
  config.yaml: |
    profiles:
    - schedulerName: default-scheduler
      plugins:
        score:
          enabled:
          - name: NodeResourcesFit
            weight: 100  # Prioritize good fit
          - name: NodeResourcesBalancedAllocation
            weight: 1    # Less important than fit
```

## Your Specific Setup Ideas

### Minimal Starting Configuration
```yaml
Control Plane: 3 small instances (t3.small)
├─ Always running
├─ Tainted to prevent workload pods
└─ ~$50/month total

Worker Nodes:
├─ general-pool: 1 node minimum (t3.large)
│   ├─ Runs frontend, API, monitoring
│   └─ Can grow to 5 nodes
│
├─ executor-pool: 0 nodes minimum
│   ├─ Scales 0→20 (c5.xlarge)
│   └─ Each executor gets own node (anti-affinity)
│
└─ gpu-pool: 0 nodes minimum
    ├─ Scales 0→5 (g4dn.xlarge)
    └─ For ML evaluations
```

### Thresholds for Scaling
```yaml
# When to add nodes (Cluster Autoscaler)
- Pending pods that can't be scheduled
- OR: Predicted capacity needed (with predictive scaling)

# When to add pods (HPA)
- CPU > 80% (traditional)
- Memory > 80%
- Queue length > 2 per executor
- Custom metrics (requests per second, etc.)

# Example HPA with multiple metrics
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50  # Scale at 50% CPU
  
  - type: Pods
    pods:
      metric:
        name: pending_jobs_per_pod
      target:
        type: AverageValue
        averageValue: "2"  # 2 jobs per pod
```

## The Beautiful Part

Once configured, it's all automatic:

1. **Queue fills up** → HPA creates pods
2. **Pods don't fit** → Cluster Autoscaler creates nodes  
3. **Work completes** → HPA removes pods
4. **Nodes empty** → Cluster Autoscaler removes nodes

You just define the rules, Kubernetes does the Tetris!