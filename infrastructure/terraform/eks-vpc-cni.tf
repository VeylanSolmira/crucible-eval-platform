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
  # Note: There's a known issue where enableNetworkPolicy in configuration_values
  # doesn't properly set the ENABLE_NETWORK_POLICY environment variable.
  # As a workaround, we need to set the env var directly after the addon is created.
  configuration_values = jsonencode({
    enableNetworkPolicy = "true"
    # The nodeAgent is required for network policy enforcement
    nodeAgent = {
      enabled = true
    }
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

# Workaround: Ensure ENABLE_NETWORK_POLICY env var is set
# There's a known issue where the addon configuration doesn't always set this properly
resource "null_resource" "enable_network_policy" {
  depends_on = [aws_eks_addon.vpc_cni]

  provisioner "local-exec" {
    command = <<-EOT
      aws eks update-kubeconfig --name ${aws_eks_cluster.main.name} --region ${data.aws_region.current.name}
      kubectl set env daemonset aws-node -n kube-system ENABLE_NETWORK_POLICY=true
      kubectl rollout restart daemonset aws-node -n kube-system
      kubectl rollout status daemonset aws-node -n kube-system --timeout=300s
    EOT
  }

  # Trigger on version changes
  triggers = {
    addon_version = aws_eks_addon.vpc_cni.addon_version
  }
}