# Kubernetes Cost Management: Pausing Infrastructure

## Quick Answer: Yes, You Can Pause!

### What You Can Pause
- **Worker Nodes**: Scale to 0 (saves ~$30-90/month)
- **Pods/Deployments**: Scale to 0 replicas
- **Cannot Pause**: EKS Control Plane ($73/month continues)

## Methods to Pause/Resume

### 1. Scale Node Group to Zero (Best Option)
```bash
# PAUSE: Scale nodes to 0
aws eks update-nodegroup-config \
  --cluster-name crucible-platform \
  --nodegroup-name crucible-platform-workers \
  --scaling-config minSize=0,maxSize=3,desiredSize=0

# RESUME: Scale back up
aws eks update-nodegroup-config \
  --cluster-name crucible-platform \
  --nodegroup-name crucible-platform-workers \
  --scaling-config minSize=1,maxSize=3,desiredSize=2
```

**Cost**: Only pay for EKS control plane ($73/month)
**Time**: ~5 minutes to scale down/up

### 2. Delete Node Group (More Aggressive)
```bash
# PAUSE: Delete entire node group
aws eks delete-nodegroup \
  --cluster-name crucible-platform \
  --nodegroup-name crucible-platform-workers

# RESUME: Recreate node group
terraform apply -target=aws_eks_node_group.main
```

**Cost**: Only pay for EKS control plane ($73/month)
**Time**: ~10 minutes to delete/recreate

### 3. Stop Individual EC2 Instances (Risky)
```bash
# Get node instance IDs
INSTANCE_IDS=$(aws ec2 describe-instances \
  --filters "Name=tag:kubernetes.io/cluster/crucible-platform,Values=owned" \
  --query 'Reservations[*].Instances[*].InstanceId' \
  --output text)

# PAUSE: Stop instances
aws ec2 stop-instances --instance-ids $INSTANCE_IDS

# RESUME: Start instances
aws ec2 start-instances --instance-ids $INSTANCE_IDS
```

**Warning**: Kubernetes doesn't handle stopped nodes well. Use scaling instead.

### 4. Delete Entire Cluster (Nuclear Option)
```bash
# PAUSE: Delete everything
eksctl delete cluster --name crucible-platform

# RESUME: Recreate
terraform apply
```

**Cost**: $0 (but lose all state)
**Time**: ~20 minutes each way

## Automated Pause/Resume Scripts

### pause-k8s.sh
```bash
#!/bin/bash
# Pause Kubernetes cluster to save costs

echo "🛑 Pausing Kubernetes cluster..."

# 1. Save current deployments state
kubectl get deployments -A -o yaml > deployments-backup.yaml

# 2. Scale all deployments to 0
kubectl scale deployments --all --replicas=0 -A

# 3. Scale node group to 0
aws eks update-nodegroup-config \
  --cluster-name crucible-platform \
  --nodegroup-name crucible-platform-workers \
  --scaling-config minSize=0,maxSize=3,desiredSize=0

echo "✅ Cluster paused. Saving ~$90/month on compute."
echo "📊 Still paying: $73/month for control plane"
```

### resume-k8s.sh
```bash
#!/bin/bash
# Resume Kubernetes cluster

echo "▶️ Resuming Kubernetes cluster..."

# 1. Scale node group back up
aws eks update-nodegroup-config \
  --cluster-name crucible-platform \
  --nodegroup-name crucible-platform-workers \
  --scaling-config minSize=1,maxSize=3,desiredSize=2

# 2. Wait for nodes to be ready
echo "⏳ Waiting for nodes..."
kubectl wait --for=condition=Ready nodes --all --timeout=300s

# 3. Restore deployments
kubectl apply -f deployments-backup.yaml

echo "✅ Cluster resumed!"
```

## Cost Comparison

| State | Monthly Cost | What's Running |
|-------|-------------|----------------|
| Full Running | ~$163 | Control plane + 2 nodes |
| Paused (nodes scaled) | $73 | Control plane only |
| Paused (stopped instances) | ~$80 | Control plane + EBS volumes |
| Deleted | $0 | Nothing |

## Terraform Configuration for Easy Pausing

Add this variable to make pausing easier:

```hcl
variable "cluster_paused" {
  description = "Set to true to pause the cluster (scale nodes to 0)"
  type        = bool
  default     = false
}

resource "aws_eks_node_group" "main" {
  # ... existing config ...
  
  scaling_config {
    desired_size = var.cluster_paused ? 0 : 2
    max_size     = 3
    min_size     = var.cluster_paused ? 0 : 1
  }
}
```

Then pause with:
```bash
terraform apply -var="cluster_paused=true"
```

## Alternative: Fargate for Sporadic Use

If you pause frequently, consider Fargate:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  annotations:
    eks.amazonaws.com/fargate-profile: crucible-fargate
```

- **Pros**: Pay only when pods run
- **Cons**: More expensive per hour, slower startup

## Schedule-Based Pausing

Automatically pause nights/weekends:

```bash
# Cron job to pause at 6 PM
0 18 * * 1-5 /home/ubuntu/scripts/pause-k8s.sh

# Resume at 8 AM
0 8 * * 1-5 /home/ubuntu/scripts/resume-k8s.sh
```

Saves ~50% on compute costs!

## Best Practices

1. **Always backup state** before pausing
2. **Use node scaling** not stopping instances
3. **Keep control plane** running (it's the cheap part)
4. **Document your pause state** so you remember
5. **Test resume process** before relying on it

## Quick Commands Cheat Sheet

```bash
# Check current costs
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --filter file://eks-filter.json

# Scale to zero (pause)
eksctl scale nodegroup --cluster=crucible-platform --name=workers --nodes=0

# Scale back up (resume)  
eksctl scale nodegroup --cluster=crucible-platform --name=workers --nodes=2

# Check node status
kubectl get nodes
```

## The Economics

- **Always On**: $163/month = $5.43/day
- **Paused Nights/Weekends**: ~$100/month (40% savings)
- **Paused Except Active Dev**: ~$80/month (50% savings)
- **Deleted Between Projects**: $0/month (100% savings)

For learning, pausing when not actively using it makes total sense!