# GitHub Actions OIDC Provider for AWS
# This allows GitHub Actions to authenticate to AWS without storing credentials

# Create the OIDC provider
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
  
  client_id_list = ["sts.amazonaws.com"]
  
  # GitHub's OIDC thumbprint (this is stable and documented by GitHub)
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
  
  tags = {
    Name        = "github-actions-oidc"
    Environment = var.environment
    Purpose     = "Allow GitHub Actions to authenticate to AWS"
  }
}

# IAM Role that GitHub Actions can assume
resource "aws_iam_role" "github_actions" {
  name               = "${var.environment}-github-actions-crucible"
  description        = "Role for GitHub Actions to deploy Crucible Platform"
  
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
          # Replace with your actual GitHub org/repo
          "token.actions.githubusercontent.com:sub" = "repo:VeylanSolmira/metr-eval-platform:*"
        }
      }
    }]
  })
  
  tags = {
    Name        = "github-actions-role"
    Environment = var.environment
    Purpose     = "Deploy Crucible Platform from GitHub Actions"
  }
}

# Policy for GitHub Actions role - what it can do
resource "aws_iam_role_policy" "github_actions" {
  name = "crucible-deployment-permissions"
  role = aws_iam_role.github_actions.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # S3 permissions for deployment
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.deployment.arn,
          "${aws_s3_bucket.deployment.arn}/*"
        ]
      },
      {
        # SSM permissions for parameters
        Effect = "Allow"
        Action = [
          "ssm:PutParameter",
          "ssm:GetParameter"
        ]
        Resource = [
          "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/crucible/*"
        ]
      },
      {
        # ECR login permission (requires * resource)
        Effect = "Allow"
        Action = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        # ECR permissions for specific repository
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = aws_ecr_repository.crucible_platform.arn
      },
      {
        # SSM permissions for Docker deployment commands
        Effect = "Allow"
        Action = [
          "ssm:SendCommand",
          "ssm:GetCommandInvocation",
          "ssm:ListCommandInvocations"
        ]
        Resource = [
          "arn:aws:ssm:${data.aws_region.current.name}::document/AWS-RunShellScript",
          "arn:aws:ec2:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:instance/*",
          "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:command/*"
        ]
      },
      {
        # EC2 permissions to find instances
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ssm:DescribeInstanceInformation"
        ]
        Resource = "*"
      },
    ]
  })
}

# Data source for current region
data "aws_region" "current" {}

# Output the role ARN for use in GitHub
output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
  description = "ARN of the IAM role for GitHub Actions. Add this to your GitHub repository variables as AWS_ROLE_ARN"
}

# Output for documentation
output "github_oidc_setup_instructions" {
  value = <<-EOT
    
    GitHub OIDC Setup Complete!
    
    1. The role ARN is: ${aws_iam_role.github_actions.arn}
    
    2. Add this as a GitHub repository variable (not secret):
       - Go to: Settings → Secrets and variables → Actions → Variables tab
       - Add variable: AWS_ROLE_ARN = ${aws_iam_role.github_actions.arn}
    
    3. Update your GitHub Actions workflow to use OIDC (already done in deploy.yml)
    
    4. No AWS credentials needed in GitHub Secrets!
  EOT
}