# AWS VPC CNI NetworkPolicy Setup Guide

## Overview
AWS VPC CNI supports NetworkPolicy enforcement but requires specific configuration. There's a known issue where the addon configuration doesn't properly set the required environment variable.

## Configuration Steps

### 1. Enable NetworkPolicy in EKS Addon (Terraform)

```hcl
resource "aws_eks_addon" "vpc_cni" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "vpc-cni"
  addon_version = data.aws_eks_addon_version.vpc_cni.version
  
  configuration_values = jsonencode({
    enableNetworkPolicy = "true"
    nodeAgent = {
      enabled = true
    }
  })
  
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"
}
```

### 2. Apply the Workaround (Required!)

Due to a known AWS issue, you must manually set the environment variable:

```hcl
resource "null_resource" "enable_network_policy" {
  depends_on = [aws_eks_addon.vpc_cni]
  
  provisioner "local-exec" {
    command = <<-EOT
      aws eks update-kubeconfig --name ${aws_eks_cluster.main.name} --region ${var.region}
      kubectl set env daemonset aws-node -n kube-system ENABLE_NETWORK_POLICY=true
      kubectl rollout restart daemonset aws-node -n kube-system
      kubectl rollout status daemonset aws-node -n kube-system --timeout=300s
    EOT
  }
  
  triggers = {
    addon_version = aws_eks_addon.vpc_cni.addon_version
  }
}
```

### 3. Alternative: Manual Setup

```bash
# Set the environment variable
kubectl set env daemonset aws-node -n kube-system ENABLE_NETWORK_POLICY=true

# Restart aws-node pods
kubectl rollout restart daemonset aws-node -n kube-system

# Wait for rollout
kubectl rollout status daemonset aws-node -n kube-system --timeout=300s
```

## Verification Steps

### 1. Check Environment Variable
```bash
kubectl get daemonset aws-node -n kube-system -o yaml | grep ENABLE_NETWORK_POLICY
# Should show: value: "true"
```

### 2. Verify PolicyEndpoint CRD
```bash
kubectl get crd policyendpoints.networking.k8s.aws
# Should exist
```

### 3. Check Network Policy Agent Logs
```bash
kubectl logs -n kube-system -l k8s-app=aws-node -c aws-eks-nodeagent --tail=50
# Look for network policy initialization messages
```

### 4. Test NetworkPolicy Creation
```bash
# Apply a test NetworkPolicy
kubectl apply -f test-network-policy.yaml

# Check if PolicyEndpoints are created
kubectl get policyendpoints -n dev
# Should see endpoints being created
```

## Known Issues

### Issue: Configuration Values Not Applied
The `enableNetworkPolicy` configuration value doesn't always properly set the `ENABLE_NETWORK_POLICY` environment variable on the aws-node DaemonSet.

**Root Cause**: Gap between what the API accepts and what actually works
**Workaround**: Manually set the environment variable as shown above

### Issue: PolicyEndpoints Empty
Even with NetworkPolicy enabled, PolicyEndpoints might not contain the expected rules.

**Possible Causes**:
- eBPF programs not loaded
- Node restart required
- Incorrect pod labels

## Troubleshooting

### If NetworkPolicy isn't working:

1. **Restart everything**:
```bash
kubectl delete pods -n kube-system -l k8s-app=aws-node
kubectl wait --for=condition=ready pods -n kube-system -l k8s-app=aws-node --timeout=120s
```

2. **Reinstall the addon**:
```bash
aws eks delete-addon --cluster-name YOUR_CLUSTER --addon-name vpc-cni
# Wait 60 seconds
aws eks create-addon \
  --cluster-name YOUR_CLUSTER \
  --addon-name vpc-cni \
  --configuration-values '{"enableNetworkPolicy":"true"}'
```

3. **Check eBPF programs**:
```bash
# Check metrics endpoint
kubectl port-forward -n kube-system pod/aws-node-xxxx 8162:8162
curl http://localhost:8162/metrics | grep ebpf
```

## Limitations

**Important**: AWS VPC CNI NetworkPolicy only controls:
- ✅ Pod-to-pod traffic within the cluster
- ✅ Pod-to-service traffic within the cluster
- ❌ External internet traffic (NOT blocked)
- ❌ EC2 Instance Metadata Service (169.254.169.254)

For complete isolation including internet blocking, consider using Calico alongside VPC CNI.