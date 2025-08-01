# ECR Repository for Test Runner Images
# This is separate from the service repositories because test runner images
# have different lifecycle requirements and tagging patterns

resource "aws_ecr_repository" "test_runner" {
  name                 = "test-runner"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  lifecycle {
    prevent_destroy = false
  }

  tags = merge(local.common_tags, {
    Name    = "test-runner-ecr"
    Purpose = "Container image for test execution"
    Type    = "test"
  })
}

# ECR Lifecycle Policy for test-runner repository
resource "aws_ecr_lifecycle_policy" "test_runner" {
  repository = aws_ecr_repository.test_runner.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 10
        description  = "Keep only the last 30 tagged images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v", "pr-", "release-", "staging-", "prod-", "dev-", "test-", "feature-", "hotfix-", "main"]
          countType     = "imageCountMoreThan"
          countNumber   = 30
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 20
        description  = "Keep the latest tag always"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["latest"]
          countType     = "imageCountMoreThan"
          countNumber   = 1
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 30
        description  = "Remove untagged images after 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 100
        description  = "Remove all images older than 7 days"
        selection = {
          tagStatus   = "any"
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

# ECR Repository Policy for test-runner - Allow GitHub Actions push and EKS pull
resource "aws_ecr_repository_policy" "test_runner" {
  repository = aws_ecr_repository.test_runner.name

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

# Output the test-runner repository URL
output "ecr_test_runner_url" {
  description = "URL of the ECR test-runner repository"
  value       = aws_ecr_repository.test_runner.repository_url
}