# Simple Explanation: Kubernetes Infrastructure

## The Basic Relationship

**EC2 Instances = Nodes = The actual computers**
**Pods = Your applications running on those computers**

Think of it like this:
- EC2 instances are apartments buildings
- Pods are tenants
- Kubernetes is the property manager

## Your Specific Questions

### "Do you have to pre-provision those EC2 instances?"

**Short answer: No!** You have three options:

1. **Fixed Pool**: "I always want 5 instances running"
   - Pros: Instant pod scheduling
   - Cons: Pay even when idle

2. **Dynamic Scaling**: "Start with 2, grow to 20 as needed"
   - Pros: Balance cost and performance
   - Cons: 2-4 minute delay for new instances

3. **Scale from Zero**: "Start with 0, create when needed"
   - Pros: Maximum cost savings
   - Cons: First job waits 2-4 minutes

### "What if we wanted every executor on its own instance?"

You can achieve this with pod anti-affinity:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: executor
spec:
  template:
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: executor
            topologyKey: kubernetes.io/hostname  # Don't put two executors on same node
```

Combined with cluster autoscaling, this forces Kubernetes to:
1. Try to schedule executor pod
2. See no nodes have space (due to anti-affinity)
3. Request new EC2 instance
4. Place executor on new instance

### "Maybe of different sizes"

Yes! You define node pools with different instance types:

```yaml
# In your infrastructure code
nodePools:
  - name: small-executors
    instanceTypes: ["t3.large"]     # 2 CPU, 8GB RAM
    labels:
      executor-size: small
    
  - name: large-executors  
    instanceTypes: ["c5.4xlarge"]   # 16 CPU, 32GB RAM
    labels:
      executor-size: large
      
  - name: gpu-executors
    instanceTypes: ["g4dn.xlarge"]  # GPU instances
    labels:
      executor-size: gpu
```

Then your pods request specific node types:

```yaml
# Small evaluation
apiVersion: batch/v1
kind: Job
metadata:
  name: eval-12345
spec:
  template:
    spec:
      nodeSelector:
        executor-size: small  # Goes to t3.large instance
        
---
# Large evaluation
apiVersion: batch/v1
kind: Job  
metadata:
  name: eval-67890
spec:
  template:
    spec:
      nodeSelector:
        executor-size: large  # Goes to c5.4xlarge instance
```

## Real-World Example Flow

Let's say user submits 5 evaluations:

```
Time    | What Happens
--------|----------------------------------------------------------
0:00    | API receives 5 evaluation requests
0:01    | Creates 5 Kubernetes Jobs
0:02    | Scheduler tries to place pods - no space available
0:03    | Cluster Autoscaler sees 5 pending pods
0:04    | Decides to launch 3 new c5.xlarge instances
0:05    | AWS starts booting the EC2 instances
2:30    | EC2 instances are running
3:00    | Instances join Kubernetes cluster as nodes
3:15    | Scheduler places pods on the new nodes
3:30    | Evaluations start running
15:00   | Evaluations complete
20:00   | No new jobs for 5 minutes, scale down begins
20:30   | EC2 instances terminated
```

## Cost Example

**Without dynamic scaling:**
- 5 c5.xlarge instances running 24/7
- Cost: ~$600/month

**With scale-to-zero:**
- 0 instances when idle
- 3 instances for ~20 minutes per batch
- Cost: ~$10/month (assuming 10 batches daily)

## The "Kubernetes Process"

You asked about "the kubernetes process running on some ec2 instance":

- **Control Plane** (3 EC2 instances): Runs Kubernetes management
  - API server (receives kubectl commands)
  - Scheduler (decides where pods go)
  - Controller manager (ensures desired state)
  
- **Worker Nodes** (N EC2 instances): Run your actual workloads
  - kubelet (manages pods on this node)
  - Container runtime (runs the containers)
  - Your pods (frontend, API, executors)

## For Your Architecture

```yaml
Frontend & API:
  - Always running on 2-3 small instances (t3.large)
  - These handle regular traffic
  
Executors:
  - Scale from 0 to many based on queue
  - Each can be on its own instance if needed
  - Different instance types for different job sizes
  - Spot instances to save 70-90% on cost
```