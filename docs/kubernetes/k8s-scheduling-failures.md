# What Happens When Pods Can't Be Scheduled

## The Decision Tree

```
Pod submitted to Kubernetes
    ↓
Scheduler tries to find a node
    ↓
Can any existing node fit this pod?
    ├─ YES → Schedule on best node → Running
    └─ NO → Pod enters "Pending" state
             ↓
         Cluster Autoscaler checks
             ↓
         Can I create a new node that would fit?
             ├─ YES → Are we under max nodes limit?
             │   ├─ YES → Create node → Wait 2-4min → Schedule pod
             │   └─ NO → Pod stays Pending (budget exhausted)
             └─ NO → Pod stays Pending (no suitable instance types)
```

## Pending States and Reasons

### 1. Insufficient Resources
```bash
$ kubectl describe pod executor-12345
Status: Pending
Events:
  Warning  FailedScheduling  pod/executor-12345  
  0/10 nodes are available: 10 Insufficient cpu.
```

### 2. Node Selector Not Matched
```bash
Events:
  Warning  FailedScheduling  pod/gpu-job-789
  0/10 nodes are available: 10 node(s) didn't match 
  node selector "nvidia.com/gpu: true"
```

### 3. Taints Not Tolerated
```bash
Events:
  Warning  FailedScheduling  pod/frontend-abc
  0/5 nodes are available: 3 node(s) had taint 
  {dedicated: gpu}, that the pod didn't tolerate
```

### 4. Autoscaler Limits Reached
```bash
$ kubectl logs -n kube-system cluster-autoscaler-xxx | grep "reason"
"reason: max node group size reached"
"reason: max cluster size (100) reached"
```

## Configuration Examples

### Node Group Limits
```hcl
# Terraform AWS example
resource "aws_autoscaling_group" "workers" {
  name     = "k8s-workers"
  min_size = 0
  max_size = 50  # Hard limit!
  
  # Optional: Protect from scale-in
  protect_from_scale_in = false
  
  # Optional: Mixed instance types
  mixed_instances_policy {
    instances_distribution {
      on_demand_base_capacity = 2  # Always keep 2 on-demand
      spot_allocation_strategy = "capacity-optimized"
    }
  }
}
```

### Budget Controls

#### Option 1: Namespace Resource Quotas
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: executor-quota
  namespace: evaluations
spec:
  hard:
    requests.cpu: "100"     # Max 100 CPUs total
    requests.memory: "200Gi" # Max 200GB RAM total
    persistentvolumeclaims: "10"
    pods: "50"              # Max 50 pods
```

#### Option 2: Priority Classes
```yaml
# Low priority pods get evicted when high priority need space
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: low-priority
value: 10
globalDefault: false
description: "Low priority evaluations"

---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000
description: "Critical system pods"
```

#### Option 3: Pod Disruption Budgets
```yaml
# Protect minimum running pods
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: frontend-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: frontend
```

## What Happens at Each Limit

### 1. Node Group Max Reached
```yaml
# Node group at max (e.g., 20/20 nodes)
Events:
  Normal   NotTriggerScaleUp  cluster-autoscaler
  pod didn't trigger scale-up (max node group size reached)
  
# Pod stays Pending indefinitely until:
# - Another pod is deleted
# - Node group max is increased
# - Pod is deleted
```

### 2. Cluster Total Max Reached
```yaml
# Total cluster at max (e.g., 100/100 nodes across all groups)
Events:
  Normal   NotTriggerScaleUp  cluster-autoscaler
  pod didn't trigger scale-up (max cluster size reached)
```

### 3. Quota Exceeded
```yaml
# Namespace quota exceeded
Error creating: pods "executor-999" is forbidden: 
exceeded quota: executor-quota, requested: requests.cpu=4, 
used: requests.cpu=98, limited: requests.cpu=100
```

### 4. Insufficient Capacity (AWS)
```yaml
# AWS can't provide the instance type
Events:
  Warning  FailedScaleUp  cluster-autoscaler
  InsufficientInstanceCapacity: We currently do not have 
  sufficient c5.24xlarge capacity in the Availability Zone
```

## Handling Pending Pods

### 1. Manual Intervention Options
```bash
# Check why pods are pending
kubectl get pods --field-selector=status.phase=Pending

# Get detailed events
kubectl describe pod <pod-name>

# Check cluster autoscaler logs
kubectl logs -n kube-system deployment/cluster-autoscaler

# Manually increase limits
kubectl edit deployment cluster-autoscaler
# Update: --nodes=0:50:workers → --nodes=0:100:workers
```

### 2. Automated Handling
```yaml
# Job with activeDeadlineSeconds
apiVersion: batch/v1
kind: Job
spec:
  activeDeadlineSeconds: 600  # Fail if not running in 10min
  template:
    spec:
      containers:
      - name: executor
        image: executor:latest
```

### 3. Application-Level Queuing
```python
# Your API could check before creating K8s jobs
async def submit_evaluation(request):
    # Check current cluster capacity
    pending_pods = k8s_client.list_pods(
        field_selector="status.phase=Pending"
    )
    
    if len(pending_pods) > MAX_PENDING:
        return JSONResponse({
            "error": "System at capacity",
            "retry_after": 300  # Try again in 5 min
        }, status_code=503)
    
    # Create job
    k8s_client.create_job(job_spec)
```

## Cost Control Strategies

### 1. Time-Based Scaling
```yaml
# Scale down at night/weekends
apiVersion: batch/v1
kind: CronJob
metadata:
  name: scale-down-night
spec:
  schedule: "0 20 * * 1-5"  # 8 PM weekdays
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: kubectl
            image: bitnami/kubectl
            command:
            - kubectl
            - scale
            - deployment
            - executor
            - --replicas=0
```

### 2. Budget Alerts
```yaml
# Prometheus alert when spending too fast
groups:
- name: cost-alerts
  rules:
  - alert: HighNodeCount
    expr: |
      count(kube_node_info) > 80
    annotations:
      summary: "Cluster has {{ $value }} nodes (limit: 100)"
      
  - alert: HighPendingPods  
    expr: |
      count(kube_pod_status_phase{phase="Pending"}) > 20
    annotations:
      summary: "{{ $value }} pods pending - may indicate capacity issues"
```

### 3. Preemptible/Spot Instances
```hcl
# Use spot instances for executors (70-90% cheaper)
resource "aws_launch_template" "executor_spot" {
  instance_market_options {
    market_type = "spot"
    spot_options {
      max_price = "0.50"  # Max willing to pay
      spot_instance_type = "persistent"
    }
  }
}
```

## The User Experience

### Good: Clear Feedback
```json
// API response when at capacity
{
  "error": "System at capacity",
  "details": {
    "reason": "max_executors_reached",
    "current_executors": 50,
    "max_executors": 50,
    "queue_position": 12
  },
  "estimated_wait_time": 600,
  "retry_after": 60
}
```

### Better: Graceful Degradation
```python
# Fallback to smaller instance types
if not can_schedule("c5.4xlarge"):
    try_schedule("c5.2xlarge")
    
# Or queue with priority
high_priority_queue = []
low_priority_queue = []

if at_capacity():
    if user.tier == "premium":
        high_priority_queue.append(job)
    else:
        low_priority_queue.append(job)
```

### Best: Predictive Scaling
```yaml
# Scale up before hitting limits
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  behavior:
    scaleUp:
      policies:
      - type: Percent
        value: 100  # Double when needed
        periodSeconds: 60
      selectPolicy: Max  # Use most aggressive policy
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5min
```

## Summary

**What happens when limits are hit:**
1. Pods enter "Pending" state (they wait, not fail)
2. Cluster Autoscaler tries to add nodes
3. If at limit → Pods stay Pending indefinitely
4. You need monitoring/alerting to handle this

**Best practices:**
- Set reasonable limits (not too low)
- Monitor pending pods
- Provide clear user feedback
- Consider spot instances for cost
- Implement app-level queuing as backstop