# ECR Repository for Crucible Platform Container Images

resource "aws_ecr_repository" "crucible_platform" {
  name                 = var.project_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  lifecycle {
    prevent_destroy = false
  }

  tags = {
    Name        = "Crucible Platform ECR Repository"
    Environment = var.environment
    Purpose     = "Container images for Crucible platform"
  }
}

# ECR Lifecycle Policy
resource "aws_ecr_lifecycle_policy" "crucible_platform" {
  repository = aws_ecr_repository.crucible_platform.name

  policy = jsonencode({
      rules = [
        {
          rulePriority = 1
          description  = "Keep last 10 images"
          selection = {
            tagStatus     = "tagged"
            tagPrefixList = ["v"]
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

# ECR Repository Policy - Allow GitHub Actions to push
resource "aws_ecr_repository_policy" "crucible_platform" {
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
        Sid    = "AllowEC2Pull"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.eval_server.arn
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

# Output the repository URL for use in GitHub Actions
output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.crucible_platform.repository_url
}

output "ecr_repository_name" {
  description = "Name of the ECR repository"
  value       = aws_ecr_repository.crucible_platform.name
}