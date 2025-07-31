# EKS Authentication Configuration
# Manages the aws-auth ConfigMap to grant IAM roles access to the cluster

# Use the kubernetes provider to manage the aws-auth ConfigMap
resource "kubernetes_config_map" "aws_auth" {
  metadata {
    name      = "aws-auth"
    namespace = "kube-system"
  }

  data = {
    mapRoles = yamlencode([
      # Node instance role - allows nodes to join the cluster
      {
        rolearn  = aws_iam_role.eks_nodes.arn
        username = "system:node:{{EC2PrivateDNSName}}"
        groups   = ["system:bootstrappers", "system:nodes"]
      },
      # GitHub Actions role - allows GitHub to deploy
      {
        rolearn  = aws_iam_role.github_actions.arn
        username = "github-actions"
        groups   = ["system:masters"] # Full admin access - adjust as needed
      },
      # GitHub Actions Terraform Plan role - read-only access
      {
        rolearn  = aws_iam_role.github_actions_terraform_plan.arn
        username = "github-actions-terraform-plan"
        groups   = ["system:masters"] # Needs admin for terraform to manage k8s resources
      },
      # GitHub Actions Terraform Apply role - full access
      {
        rolearn  = aws_iam_role.github_actions_terraform_apply.arn
        username = "github-actions-terraform-apply"
        groups   = ["system:masters"] # Full admin access for apply
      },
      # Add more roles as needed
    ])

    # mapUsers can be added if you need to grant specific IAM users access
    # mapUsers = yamlencode([
    #   {
    #     userarn  = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:user/admin"
    #     username = "admin"
    #     groups   = ["system:masters"]
    #   }
    # ])
  }

  depends_on = [aws_eks_cluster.main]
}

# Output for documentation
output "eks_auth_info" {
  description = "Information about EKS authentication setup"
  value = {
    github_actions_role = aws_iam_role.github_actions.arn
    node_role           = aws_iam_role.eks_nodes.arn
    instructions        = <<-EOT
      The aws-auth ConfigMap has been configured to allow:
      - EKS nodes to join the cluster
      - GitHub Actions to deploy to the cluster
      
      To grant additional IAM roles access:
      1. Add them to the mapRoles in eks-auth.tf
      2. Run terraform apply
      
      To check current access:
      kubectl describe configmap aws-auth -n kube-system
    EOT
  }
}