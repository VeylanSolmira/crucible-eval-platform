# Executor Scaling Example

## The Scenario

You want executors that:
- Start at 0 replicas (no executors running)
- Scale up to 10 based on job queue length
- Each executor gets its own compute resources
- Different evaluation types might need different instance sizes

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Job Queue (Redis)                        │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                │
│  │Job 1│ │Job 2│ │Job 3│ │Job 4│ │Job 5│ ...            │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘                │
└────────────────────────────────────────────────────────────┘
                            ↓
                    HPA checks queue
                            ↓
        "5 jobs pending, but only 2 executors running"
                            ↓
                    Creates 3 more pods
                            ↓
┌────────────────────────────────────────────────────────────┐
│                 Kubernetes Scheduler                        │
│                                                            │
│  "I need to place 3 executor pods, each needs 4GB RAM"    │
│  "Current nodes are full... marking as Pending"           │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│                  Cluster Autoscaler                        │
│                                                            │
│  "I see 3 pending pods that need 'executor' nodes"        │
│  "Let me launch 2 new c5.xlarge instances"                │
└────────────────────────────────────────────────────────────┘
                            ↓
                    (2-4 minutes later)
                            ↓
┌────────────────────────────────────────────────────────────┐
│                   New EC2 Instances                        │
│  ┌─────────────────────┐    ┌─────────────────────┐      │
│  │   c5.xlarge #1      │    │   c5.xlarge #2      │      │
│  │   executor-pod-3    │    │   executor-pod-4    │      │
│  │   executor-pod-5    │    │                     │      │
│  └─────────────────────┘    └─────────────────────┘      │
└────────────────────────────────────────────────────────────┘
```

## Implementation

### 1. Node Pool Configuration (Terraform)
```hcl
resource "aws_launch_template" "executor_nodes" {
  name_prefix = "executor-node-"
  
  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size = 100  # Enough for Docker images
      volume_type = "gp3"
    }
  }
  
  # User data to join Kubernetes cluster
  user_data = base64encode(templatefile("${path.module}/user-data.sh", {
    cluster_name     = var.cluster_name
    cluster_endpoint = aws_eks_cluster.main.endpoint
  }))
}

resource "aws_autoscaling_group" "executor_nodes" {
  name               = "executor-nodes"
  min_size           = 0      # Start with zero!
  max_size           = 20     # Maximum nodes
  desired_capacity   = 0      # Start with zero!
  
  launch_template {
    id      = aws_launch_template.executor_nodes.id
    version = "$Latest"
  }
  
  # Mixed instances for different workload sizes
  mixed_instances_policy {
    instances_distribution {
      spot_allocation_strategy = "capacity-optimized"
      spot_instance_pools      = 3
    }
    
    launch_template {
      launch_template_specification {
        launch_template_id = aws_launch_template.executor_nodes.id
      }
      
      override {
        instance_type = "c5.xlarge"   # 4 vCPU, 8GB RAM
        weighted_capacity = 1
      }
      
      override {
        instance_type = "c5.2xlarge"  # 8 vCPU, 16GB RAM
        weighted_capacity = 2
      }
      
      override {
        instance_type = "c5.4xlarge"  # 16 vCPU, 32GB RAM
        weighted_capacity = 4
      }
    }
  }
  
  tag {
    key                 = "k8s.io/cluster-autoscaler/enabled"
    value               = "true"
    propagate_at_launch = true
  }
  
  tag {
    key                 = "k8s.io/cluster-autoscaler/${var.cluster_name}"
    value               = "owned"
    propagate_at_launch = true
  }
}
```

### 2. Executor Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: executor
spec:
  replicas: 0  # Start with zero
  selector:
    matchLabels:
      app: executor
  template:
    metadata:
      labels:
        app: executor
    spec:
      # Only schedule on executor nodes
      nodeSelector:
        node.kubernetes.io/instance-type: c5.xlarge
      
      # Tolerate the taint that keeps other pods off
      tolerations:
      - key: dedicated
        operator: Equal
        value: executor
        effect: NoSchedule
        
      containers:
      - name: executor
        image: crucible-platform/executor:latest
        env:
        - name: REDIS_URL
          value: redis://redis-service:6379
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "6Gi"
            cpu: "3"
```

### 3. HPA Based on Queue Length
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
  # Custom metric from queue length
  - type: External
    external:
      metric:
        name: redis_queue_length
        selector:
          matchLabels:
            queue: "evaluation-jobs"
      target:
        type: AverageValue
        averageValue: "1"  # 1 job per executor
  
  # Also consider CPU for scale-down
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 20  # Scale down if CPU < 20%
  
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30  # React quickly to new jobs
      policies:
      - type: Percent
        value: 100  # Can double the replicas
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5 min before scaling down
      policies:
      - type: Pods
        value: 1  # Remove 1 pod at a time
        periodSeconds: 60
```

### 4. Cluster Autoscaler Configuration
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
spec:
  template:
    spec:
      containers:
      - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.28.0
        name: cluster-autoscaler
        command:
        - ./cluster-autoscaler
        - --v=4
        - --stderrthreshold=info
        - --cloud-provider=aws
        - --skip-nodes-with-local-storage=false
        - --expander=least-waste
        - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/evaluation-platform
        - --scale-down-delay-after-add=5m
        - --scale-down-unneeded-time=5m
        env:
        - name: AWS_REGION
          value: us-west-2
```

## Different Evaluation Types

### Small Evaluations (Python scripts)
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: eval-small-12345
spec:
  template:
    spec:
      nodeSelector:
        node.kubernetes.io/instance-type: t3.medium
      containers:
      - name: evaluator
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
```

### Large Evaluations (Docker builds)
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: eval-large-67890
spec:
  template:
    spec:
      nodeSelector:
        node.kubernetes.io/instance-type: c5.2xlarge
      containers:
      - name: evaluator
        resources:
          requests:
            memory: "8Gi"
            cpu: "4"
```

### GPU Evaluations (ML workloads)
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: eval-gpu-11111
spec:
  template:
    spec:
      nodeSelector:
        node.kubernetes.io/instance-type: g4dn.xlarge
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
      containers:
      - name: evaluator
        resources:
          requests:
            memory: "8Gi"
            cpu: "4"
            nvidia.com/gpu: 1
```

## Scale-to-Zero Timing

```
Queue Empty → 5 min → HPA scales pods to 0
                ↓
No pods on executor nodes → 5 min → Cluster Autoscaler terminates EC2 instances
                ↓
            Total: ~10 minutes from empty queue to zero cost
```

## Faster Scaling Options

### 1. Virtual Kubelet with Fargate
- No pre-provisioning needed
- Pods start in ~30 seconds
- More expensive per compute hour

### 2. Karpenter (newer than Cluster Autoscaler)
- Smarter instance selection
- Faster scale-up (bypasses ASG)
- Better bin packing

### 3. Pre-warmed Node Pools
- Keep 1-2 nodes always running
- Instant pod scheduling
- Higher baseline cost