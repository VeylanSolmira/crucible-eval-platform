# EKS Amazon Linux 2 to Amazon Linux 2023 Migration Guide

## Overview

AWS is ending support for EKS-optimized Amazon Linux 2 (AL2) AMIs on **November 26, 2025**. This guide provides a comprehensive migration plan to Amazon Linux 2023 (AL2023) for the Crucible Platform EKS cluster.

**Current Status**: Using AL2_x86_64 AMI type  
**Target**: AL2023_x86_64 AMI type  
**Deadline**: November 26, 2025 (less than 4 months remaining as of July 31, 2025)

## Key Differences: AL2 vs AL2023

### Security Enhancements
- **SELinux**: Enabled in permissive mode by default
- **IMDSv2**: Instance Metadata Service v2 only (more secure)
- **Crypto policies**: System-wide cryptographic policies
- **Lockdown**: Kernel lockdown in integrity mode

### Package Management
- **DNF** replaces YUM (though `yum` commands still work)
- **Smaller base**: Minimal package set by default
- **Faster updates**: Improved package installation speed

### Performance
- **Boot time**: ~15-20% faster boot times
- **Memory**: Lower memory footprint
- **Container runtime**: Optimized for containers

## Pre-Migration Checklist

### 1. Inventory Current Customizations
```bash
# Check for custom user data scripts
kubectl get nodes -o yaml | grep -A20 userData

# List any DaemonSets that might install node-level software
kubectl get daemonsets --all-namespaces

# Check for any host path mounts
kubectl get pods --all-namespaces -o yaml | grep hostPath -A5
```

### 2. Review Application Compatibility
- [ ] Check if applications rely on specific AL2 packages
- [ ] Verify gVisor DaemonSet compatibility with AL2023
- [ ] Test any init containers that install packages
- [ ] Review security contexts and SELinux requirements

### 3. Backup Current Configuration
```bash
# Export current node group configuration
aws eks describe-nodegroup \
  --cluster-name crucible-platform \
  --nodegroup-name crucible-platform-workers \
  > nodegroup-backup-$(date +%Y%m%d).json

# Backup any custom launch templates
aws ec2 describe-launch-templates \
  --launch-template-names "crucible-platform-*" \
  > launch-templates-backup-$(date +%Y%m%d).json
```

## Migration Steps

### Phase 1: Development Environment Testing

#### Step 1: Update Terraform Configuration
```hcl
# In eks-minimal.tf, update the AMI type:
resource "aws_eks_node_group" "main" {
  # ... other configuration ...
  
  # Updated AMI type for AL2023
  ami_type = "AL2023_x86_64"  # Changed from AL2_x86_64
  
  # ... rest of configuration ...
}
```

#### Step 2: Create Test Node Group (Blue-Green Approach)
For safer migration, create a parallel node group:

```hcl
# Temporary AL2023 node group for testing
resource "aws_eks_node_group" "al2023_test" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.project_name}-workers-al2023"
  node_role_arn   = aws_iam_role.eks_nodes.arn
  subnet_ids      = [for s in aws_subnet.private : s.id]
  
  scaling_config {
    desired_size = 1
    max_size     = 2
    min_size     = 1
  }
  
  instance_types = ["t3.large"]
  ami_type       = "AL2023_x86_64"
  disk_size      = 20
  
  labels = {
    "node-migration" = "al2023-test"
  }
  
  taints {
    key    = "node-migration"
    value  = "al2023-test"
    effect = "NoSchedule"
  }
  
  tags = merge(local.common_tags, {
    Name    = "${var.project_name}-eks-nodes-al2023-test"
    Purpose = "AL2023 migration testing"
  })
  
  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy,
  ]
}
```

#### Step 3: Test Workloads on New Nodes
```bash
# Remove taint from one AL2023 node to allow scheduling
kubectl taint nodes <al2023-node-name> node-migration:NoSchedule-

# Create test deployment targeting AL2023 nodes
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: al2023-test
  namespace: dev
spec:
  replicas: 1
  selector:
    matchLabels:
      app: al2023-test
  template:
    metadata:
      labels:
        app: al2023-test
    spec:
      nodeSelector:
        node-migration: al2023-test
      containers:
      - name: test
        image: 503132503803.dkr.ecr.us-west-2.amazonaws.com/api:latest
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
EOF

# Monitor pod status
kubectl get pods -n dev -l app=al2023-test -w
```

### Phase 2: Gradual Migration

#### Step 1: Scale Up AL2023 Nodes
```bash
# Scale up the AL2023 node group
aws eks update-nodegroup-config \
  --cluster-name crucible-platform \
  --nodegroup-name crucible-platform-workers-al2023 \
  --scaling-config desiredSize=2,minSize=2,maxSize=3
```

#### Step 2: Cordon and Drain AL2 Nodes
```bash
# Get AL2 nodes
AL2_NODES=$(kubectl get nodes -l eks.amazonaws.com/nodegroup=crucible-platform-workers -o name)

# Cordon nodes (prevent new pods)
for node in $AL2_NODES; do
  kubectl cordon $node
done

# Drain nodes one by one
for node in $AL2_NODES; do
  kubectl drain $node \
    --ignore-daemonsets \
    --delete-emptydir-data \
    --grace-period=60
  
  # Wait for pods to stabilize
  sleep 30
done
```

#### Step 3: Delete Old Node Group
Once all workloads are running on AL2023 nodes:
```bash
# Delete the AL2 node group
aws eks delete-nodegroup \
  --cluster-name crucible-platform \
  --nodegroup-name crucible-platform-workers

# Or via Terraform: Remove the old node group configuration
```

### Phase 3: Cleanup and Validation

#### Step 1: Update Terraform Configuration
Remove the temporary test node group and update the main configuration:

```hcl
resource "aws_eks_node_group" "main" {
  # ... configuration ...
  ami_type = "AL2023_x86_64"  # Permanent change
  # ... rest of configuration ...
}
```

#### Step 2: Verify All Services
```bash
# Check all pods are running
kubectl get pods --all-namespaces | grep -v Running

# Verify node health
kubectl get nodes
kubectl describe nodes | grep -E "Ready|Pressure"

# Test critical services
kubectl exec -it deployment/api -n dev -- curl http://localhost:8080/health
kubectl exec -it deployment/dispatcher -n dev -- curl http://localhost:8090/health

# Check gVisor runtime
kubectl get pods -n kube-system -l app=gvisor-installer
```

## Rollback Plan

If issues occur during migration:

1. **Immediate Rollback** (if using blue-green approach):
   ```bash
   # Scale down AL2023 nodes
   aws eks update-nodegroup-config \
     --cluster-name crucible-platform \
     --nodegroup-name crucible-platform-workers-al2023 \
     --scaling-config desiredSize=0,minSize=0,maxSize=0
   
   # Scale up AL2 nodes
   aws eks update-nodegroup-config \
     --cluster-name crucible-platform \
     --nodegroup-name crucible-platform-workers \
     --scaling-config desiredSize=1,minSize=1,maxSize=2
   ```

2. **Terraform Rollback**:
   ```bash
   # Revert the AMI type in terraform
   git checkout HEAD~1 -- infrastructure/terraform/eks-minimal.tf
   
   # Apply the old configuration
   cd infrastructure/terraform
   tofu apply
   ```

## Known Issues and Workarounds

### 1. SELinux Compatibility
AL2023 has SELinux in permissive mode. If pods fail with permission issues:
```yaml
# Add to pod spec:
securityContext:
  seLinuxOptions:
    type: "spc_t"
```

### 2. Package Installation
If init containers fail to install packages:
```dockerfile
# AL2: yum install -y package-name
# AL2023: dnf install -y package-name
# Both work, but dnf is preferred
```

### 3. Instance Metadata Service
AL2023 enforces IMDSv2. Update any scripts using metadata:
```bash
# Old (IMDSv1):
curl http://169.254.169.254/latest/meta-data/instance-id

# New (IMDSv2):
TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id
```

## Post-Migration Tasks

1. **Update Documentation**:
   - Update README with AL2023 requirements
   - Document any behavior changes

2. **Update CI/CD**:
   - Test that GitHub Actions deployments work
   - Verify any node-specific scripts

3. **Monitor Performance**:
   - Track boot times
   - Monitor memory usage
   - Check for any performance regressions

4. **Security Audit**:
   - Review SELinux audit logs
   - Verify IMDSv2 enforcement
   - Check security scanning results

## Timeline Recommendation

Given the November 26, 2025 deadline:

- **Week 1-2 (Early August)**: Test in development
- **Week 3-4 (Mid August)**: Migrate development environment
- **Week 5-6 (Late August)**: Test in staging
- **Week 7-8 (Early September)**: Migrate staging
- **Week 9-10 (Mid September)**: Production migration
- **Week 11-12 (Late September)**: Monitor and optimize

This provides a 2-month buffer before the deadline for any issues.

## Additional Resources

- [AWS EKS AL2 Deprecation FAQ](https://docs.aws.amazon.com/eks/latest/userguide/eks-ami-deprecation-faqs.html)
- [Amazon Linux 2023 User Guide](https://docs.aws.amazon.com/linux/al2023/ug/what-is-amazon-linux.html)
- [EKS Optimized AL2023 AMI](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html)
- [Migrating from AL2 to AL2023](https://aws.amazon.com/blogs/containers/amazon-eks-optimized-amazon-linux-2023-amis-now-available/)