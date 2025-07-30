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
  name        = "${var.environment}-github-actions-crucible"
  description = "Role for GitHub Actions to deploy Crucible Platform"

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
          "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/*"
        ]
      },
      {
        # ECR login permission (requires * resource)
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        # ECR permissions for all repositories
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:DescribeRepositories",
          "ecr:DescribeImages",
          "ecr:ListImages",
          "ecr:StartImageScan"
        ]
        Resource = [
          "arn:aws:ecr:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:repository/*"
        ]
      },
      {
        # SSM SendCommand permissions with specific resources
        Effect = "Allow"
        Action = [
          "ssm:SendCommand"
        ]
        Resource = [
          "arn:aws:ssm:${data.aws_region.current.name}::document/AWS-RunShellScript",
          "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:instance/*",
          "arn:aws:ec2:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:instance/*"
        ]
      },
      {
        # SSM GetCommandInvocation requires broader permissions
        # Using account-scoped wildcard for security (not global *)
        # See: docs/security/aws-permissions.md#ssm-permissions
        Effect = "Allow"
        Action = [
          "ssm:GetCommandInvocation"
        ]
        Resource = [
          "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"
        ]
      },
      {
        # EC2 permissions for Terraform - read
        Effect = "Allow"
        Action = [
          "ec2:Describe*",
          "ssm:DescribeInstanceInformation"
        ]
        Resource = "*"
      },
      {
        # EC2 permissions for Terraform - write
        Effect = "Allow"
        Action = [
          "ec2:CreateVpc",
          "ec2:CreateSubnet",
          "ec2:CreateInternetGateway",
          "ec2:CreateRouteTable",
          "ec2:CreateRoute",
          "ec2:CreateSecurityGroup",
          "ec2:CreateTags",
          "ec2:ModifyVpcAttribute",
          "ec2:ModifySubnetAttribute",
          "ec2:AttachInternetGateway",
          "ec2:AssociateRouteTable",
          "ec2:AuthorizeSecurityGroupIngress",
          "ec2:AuthorizeSecurityGroupEgress",
          "ec2:RevokeSecurityGroupIngress",
          "ec2:RevokeSecurityGroupEgress",
          "ec2:DeleteSecurityGroup",
          "ec2:ImportKeyPair",
          "ec2:DeleteKeyPair",
          "ec2:RunInstances",
          "ec2:TerminateInstances",
          "ec2:StopInstances",
          "ec2:StartInstances",
          "ec2:RebootInstances",
          "ec2:ModifyInstanceAttribute",
          "ec2:CreateSnapshot",
          "ec2:DeleteSnapshot",
          "ec2:CreateVolume",
          "ec2:DeleteVolume",
          "ec2:AttachVolume",
          "ec2:DetachVolume"
        ]
        Resource = "*"
      },
      {
        # EKS permissions for Terraform
        Effect = "Allow"
        Action = [
          "eks:CreateCluster",
          "eks:DeleteCluster",
          "eks:DescribeCluster",
          "eks:UpdateClusterConfig",
          "eks:UpdateClusterVersion",
          "eks:AccessKubernetesApi",
          "eks:CreateNodegroup",
          "eks:DeleteNodegroup",
          "eks:DescribeNodegroup",
          "eks:UpdateNodegroupConfig",
          "eks:UpdateNodegroupVersion",
          "eks:TagResource",
          "eks:UntagResource"
        ]
        Resource = [
          "arn:aws:eks:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:cluster/*",
          "arn:aws:eks:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:nodegroup/*/*/*"
        ]
      },
      {
        # EKS ListClusters requires * resource
        Effect = "Allow"
        Action = [
          "eks:ListClusters",
          "eks:DescribeAddonVersions"
        ]
        Resource = "*"
      },
      {
        # IAM permissions for Terraform - read
        Effect = "Allow"
        Action = [
          "iam:GetRole",
          "iam:GetRolePolicy",
          "iam:ListRolePolicies",
          "iam:ListAttachedRolePolicies",
          "iam:GetOpenIDConnectProvider",
          "iam:ListOpenIDConnectProviders",
          "iam:GetPolicy",
          "iam:GetPolicyVersion",
          "iam:ListPolicyVersions",
          "iam:GetInstanceProfile",
          "iam:ListInstanceProfiles"
        ]
        Resource = "*"
      },
      {
        # IAM permissions for Terraform - write
        Effect = "Allow"
        Action = [
          "iam:CreateRole",
          "iam:UpdateRole",
          "iam:DeleteRole",
          "iam:PutRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy",
          "iam:CreatePolicy",
          "iam:UpdatePolicy",
          "iam:DeletePolicy",
          "iam:CreatePolicyVersion",
          "iam:DeletePolicyVersion",
          "iam:SetDefaultPolicyVersion",
          "iam:CreateInstanceProfile",
          "iam:DeleteInstanceProfile",
          "iam:AddRoleToInstanceProfile",
          "iam:RemoveRoleFromInstanceProfile",
          "iam:PassRole",
          "iam:TagRole",
          "iam:UntagRole"
        ]
        Resource = [
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*",
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/*",
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:instance-profile/*"
        ]
      },
      {
        # Route53 permissions for reading zones (needed by Terraform)
        Effect = "Allow"
        Action = [
          "route53:GetHostedZone",
          "route53:ListHostedZones",
          "route53:ListResourceRecordSets",
          "route53:GetHealthCheck",
          "route53:ListHealthChecks"
        ]
        Resource = "*"
      },
      {
        # CloudWatch permissions for monitoring
        Effect = "Allow"
        Action = [
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics",
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      },
      {
        # Autoscaling permissions (for reading node groups)
        Effect = "Allow"
        Action = [
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:DescribeLaunchConfigurations",
          "autoscaling:DescribeTags"
        ]
        Resource = "*"
      },
      {
        # ElasticLoadBalancing permissions (for ALBs)
        Effect = "Allow"
        Action = [
          "elasticloadbalancing:DescribeLoadBalancers",
          "elasticloadbalancing:DescribeTargetGroups",
          "elasticloadbalancing:DescribeTargetHealth",
          "elasticloadbalancing:DescribeListeners",
          "elasticloadbalancing:DescribeRules"
        ]
        Resource = "*"
      },
      {
        # KMS permissions for encryption keys
        Effect = "Allow"
        Action = [
          "kms:DescribeKey",
          "kms:GetKeyPolicy",
          "kms:GetKeyRotationStatus",
          "kms:ListAliases",
          "kms:ListKeys"
        ]
        Resource = "*"
      },
      {
        # S3 permissions for Terraform state
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:GetBucketVersioning",
          "s3:ListBucketVersions"
        ]
        Resource = "arn:aws:s3:::crucible-platform-terraform-state-503132503803"
      },
      {
        # Organizations permissions (for account info)
        Effect = "Allow"
        Action = [
          "organizations:DescribeOrganization",
          "account:GetContactInformation"
        ]
        Resource = "*"
      },
      {
        # STS permissions for identity info
        Effect = "Allow"
        Action = [
          "sts:GetCallerIdentity"
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
  value       = aws_iam_role.github_actions.arn
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