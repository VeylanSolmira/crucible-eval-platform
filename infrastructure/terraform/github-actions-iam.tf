# GitHub Actions OIDC Provider and IAM Roles
# This creates separate roles for different GitHub Actions jobs
# following the principle of least privilege

# Data source is already defined in main.tf
# OIDC provider is already defined in github-oidc.tf

# Terraform Plan Role (Read-Only)
resource "aws_iam_role" "github_actions_terraform_plan" {
  name = "${var.project_name}-github-actions-terraform-plan"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository_name}:*"
        }
      }
    }]
  })

  tags = merge(local.common_tags, {
    Name    = "${var.project_name}-github-actions-terraform-plan"
    Purpose = "Read-only role for terraform plan"
  })
}

# Attach read-only policy to plan role
resource "aws_iam_role_policy" "github_actions_terraform_plan" {
  name = "terraform-plan-policy"
  role = aws_iam_role.github_actions_terraform_plan.id

  policy = file("${path.module}/iam-policies/github-actions-terraform-read.json")
}

# Terraform Apply Role (Write Access)
resource "aws_iam_role" "github_actions_terraform_apply" {
  name = "${var.project_name}-github-actions-terraform-apply"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          # Only allow from main branch or specific environments
          "token.actions.githubusercontent.com:sub" = [
            "repo:${var.github_repository_name}:ref:refs/heads/main",
            "repo:${var.github_repository_name}:environment:production"
          ]
        }
      }
    }]
  })

  tags = merge(local.common_tags, {
    Name    = "${var.project_name}-github-actions-terraform-apply"
    Purpose = "Write access role for terraform apply"
  })
}

# Attach write policy to apply role
resource "aws_iam_role_policy" "github_actions_terraform_apply" {
  name = "terraform-apply-policy"
  role = aws_iam_role.github_actions_terraform_apply.id

  policy = file("${path.module}/iam-policies/github-actions-terraform-write.json")
}

# Output the role ARNs for GitHub Actions configuration
output "github_actions_terraform_plan_role_arn" {
  description = "ARN of the GitHub Actions role for terraform plan"
  value       = aws_iam_role.github_actions_terraform_plan.arn
}

output "github_actions_terraform_apply_role_arn" {
  description = "ARN of the GitHub Actions role for terraform apply"
  value       = aws_iam_role.github_actions_terraform_apply.arn
}

# Instructions for setting up GitHub repository variables
output "github_actions_setup_instructions" {
  description = "Instructions for configuring GitHub Actions"
  value       = <<EOF
To use these roles in GitHub Actions:

1. Go to your GitHub repository settings
2. Navigate to Settings -> Secrets and variables -> Actions -> Variables
3. Add these repository variables:
   - AWS_TERRAFORM_PLAN_ROLE_ARN: ${aws_iam_role.github_actions_terraform_plan.arn}
   - AWS_TERRAFORM_APPLY_ROLE_ARN: ${aws_iam_role.github_actions_terraform_apply.arn}

The workflow will automatically use the appropriate role based on the job.
EOF
}