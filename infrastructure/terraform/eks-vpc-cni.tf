# VPC CNI Addon Configuration
# This manages the Amazon VPC CNI plugin for Kubernetes
# which provides native VPC networking for pods

# Get the latest version of the VPC CNI addon
data "aws_eks_addon_version" "vpc_cni" {
  addon_name         = "vpc-cni"
  kubernetes_version = aws_eks_cluster.main.version
  most_recent        = true
}

# Configure the VPC CNI addon with NetworkPolicy support enabled
resource "aws_eks_addon" "vpc_cni" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "vpc-cni"

  # Use the latest compatible version
  addon_version = data.aws_eks_addon_version.vpc_cni.version

  # Enable NetworkPolicy support
  configuration_values = jsonencode({
    enableNetworkPolicy = "true"
    # You can add other VPC CNI configurations here as needed
    # For example:
    # enablePodENI = "true"  # For Security Groups for Pods
    # nodeAgentEnabled = "true"  # For Network Policy enforcement
  })

  # Handle conflicts by overwriting
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  # Preserve the existing service account
  preserve = true

  tags = local.common_tags
}

# Output the VPC CNI addon version
output "vpc_cni_addon_version" {
  description = "The version of the VPC CNI addon"
  value       = aws_eks_addon.vpc_cni.addon_version
}

# Output whether NetworkPolicy is enabled
output "network_policy_enabled" {
  description = "Whether NetworkPolicy enforcement is enabled in the VPC CNI"
  value       = "true"
}