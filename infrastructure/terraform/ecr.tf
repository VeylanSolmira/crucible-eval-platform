# ECR Repositories for Crucible Platform Container Images

# Define the services that need ECR repositories
locals {
  services = [
    "api",
    "frontend", 
    "storage-service",
    "storage-worker",
    "celery-worker",
    "dispatcher",
    "cleanup-controller"
  ]
  
  executor_images = [
    "executor-base",
    "executor-ml"
  ]
  
  # Base images used for building other images
  base_images = [
    "base"
  ]
}

# ECR Repositories for each service
resource "aws_ecr_repository" "services" {
  for_each = toset(local.services)
  
  name                 = each.key
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  lifecycle {
    prevent_destroy = false
  }

  tags = merge(local.common_tags, {
    Name        = "${each.key}-ecr"
    Purpose     = "Container image for ${each.key} service"
    Service     = each.key
  })
}

# ECR Repositories for executor images
resource "aws_ecr_repository" "executors" {
  for_each = toset(local.executor_images)
  
  name                 = each.key
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  lifecycle {
    prevent_destroy = false
  }

  tags = merge(local.common_tags, {
    Name        = "${each.key}-ecr"
    Purpose     = "Executor image for evaluations"
    Type        = "executor"
  })
}

# ECR Repositories for base images
resource "aws_ecr_repository" "base_images" {
  for_each = toset(local.base_images)
  
  name                 = each.key
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  lifecycle {
    prevent_destroy = false
  }

  tags = merge(local.common_tags, {
    Name        = "${each.key}-ecr"
    Purpose     = "Base image for building services"
    Type        = "base"
  })
}

# ECR Lifecycle Policy for service repositories
resource "aws_ecr_lifecycle_policy" "services" {
  for_each   = aws_ecr_repository.services
  repository = each.value.name

  policy = jsonencode({
      rules = [
        {
          rulePriority = 1
          description  = "Keep last 10 images per tag prefix"
          selection = {
            tagStatus     = "tagged"
            tagPrefixList = ["dev", "staging", "prod"]
            countType     = "imageCountMoreThan"
            countNumber   = 10
          }
          action = {
            type = "expire"
          }
        },
        {
          rulePriority = 2
          description  = "Remove untagged images after 7 days"
          selection = {
            tagStatus   = "untagged"
            countType   = "sinceImagePushed"
            countUnit   = "days"
            countNumber = 7
          }
          action = {
            type = "expire"
          }
        }
      ]
    })
}

# ECR Lifecycle Policy for executor repositories
resource "aws_ecr_lifecycle_policy" "executors" {
  for_each   = aws_ecr_repository.executors
  repository = each.value.name

  policy = jsonencode({
      rules = [
        {
          rulePriority = 1
          description  = "Keep last 20 executor images"
          selection = {
            tagStatus     = "any"
            countType     = "imageCountMoreThan"
            countNumber   = 20
          }
          action = {
            type = "expire"
          }
        }
      ]
    })
}

# ECR Lifecycle Policy for base images
resource "aws_ecr_lifecycle_policy" "base_images" {
  for_each   = aws_ecr_repository.base_images
  repository = each.value.name

  policy = jsonencode({
      rules = [
        {
          rulePriority = 1
          description  = "Keep last 5 base images"
          selection = {
            tagStatus     = "any"
            countType     = "imageCountMoreThan"
            countNumber   = 5
          }
          action = {
            type = "expire"
          }
        }
      ]
    })
}

# ECR Repository Policy for service repositories - Allow GitHub Actions and EKS to pull
resource "aws_ecr_repository_policy" "services" {
  for_each   = aws_ecr_repository.services
  repository = each.value.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowGitHubActionsPush"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.github_actions.arn
        }
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
      },
      {
        Sid    = "AllowEKSNodesPull"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.eks_nodes.arn
        }
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
      }
    ]
  })
}

# ECR Repository Policy for executor repositories
resource "aws_ecr_repository_policy" "executors" {
  for_each   = aws_ecr_repository.executors
  repository = each.value.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowGitHubActionsPush"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.github_actions.arn
        }
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
      },
      {
        Sid    = "AllowEKSNodesPull"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.eks_nodes.arn
        }
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
      }
    ]
  })
}

# ECR Repository Policy for base images - Allow GitHub Actions push and everyone pull
resource "aws_ecr_repository_policy" "base_images" {
  for_each   = aws_ecr_repository.base_images
  repository = each.value.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowGitHubActionsPush"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.github_actions.arn
        }
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
      },
      {
        Sid    = "AllowEKSNodesPull"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.eks_nodes.arn
        }
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
      }
    ]
  })
}

# Keep the legacy repository for backward compatibility (can be removed later)
resource "aws_ecr_repository" "crucible_platform" {
  name                 = var.project_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  lifecycle {
    prevent_destroy = false
  }

  tags = merge(local.common_tags, {
    Name        = "${var.project_name}-ecr"
    Purpose     = "Legacy repository - to be removed"
    Deprecated  = "true"
  })
}

# Legacy repository policy - Allow GitHub Actions and EKS to pull
resource "aws_ecr_repository_policy" "crucible_platform_legacy" {
  repository = aws_ecr_repository.crucible_platform.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowGitHubActionsPush"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.github_actions.arn
        }
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
      },
      {
        Sid    = "AllowEKSNodesPull"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.eks_nodes.arn
        }
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
      }
    ]
  })
}

# Output the repository URLs
output "ecr_service_urls" {
  description = "URLs of the ECR service repositories"
  value       = { for k, v in aws_ecr_repository.services : k => v.repository_url }
}

output "ecr_executor_urls" {
  description = "URLs of the ECR executor repositories"
  value       = { for k, v in aws_ecr_repository.executors : k => v.repository_url }
}

output "ecr_base_urls" {
  description = "URLs of the ECR base image repositories"
  value       = { for k, v in aws_ecr_repository.base_images : k => v.repository_url }
}

# Legacy outputs for backward compatibility
output "ecr_repository_url" {
  description = "URL of the legacy ECR repository (deprecated)"
  value       = aws_ecr_repository.crucible_platform.repository_url
}

output "ecr_repository_name" {
  description = "Name of the legacy ECR repository (deprecated)"
  value       = aws_ecr_repository.crucible_platform.name
}