# ECR Lifecycle Policies for automated image cleanup

# Lifecycle policy for test-runner images
resource "aws_ecr_lifecycle_policy" "test_runner_cleanup" {
  repository = aws_ecr_repository.crucible_platform.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 10
        description  = "Keep only the last 10 test-runner images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["test-runner-"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 20
        description  = "Remove test-runner images older than 7 days"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["test-runner-"]
          countType     = "sinceImagePushed"
          countUnit     = "days"
          countNumber   = 7
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 30
        description  = "Keep the latest tag always"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["test-runner-latest"]
          countType     = "imageCountMoreThan"
          countNumber   = 1
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}