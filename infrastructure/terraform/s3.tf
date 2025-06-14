# S3 buckets for deployment and storage

# Deployment bucket for application packages
resource "aws_s3_bucket" "deployment" {
  bucket = "${var.environment}-crucible-deployment-${data.aws_caller_identity.current.account_id}"
  
  tags = {
    Name        = "Crucible Deployment Packages"
    Environment = var.environment
    Purpose     = "Application deployment artifacts"
  }
}

# Versioning for deployment bucket
resource "aws_s3_bucket_versioning" "deployment" {
  bucket = aws_s3_bucket.deployment.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Encryption for deployment bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "deployment" {
  bucket = aws_s3_bucket.deployment.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle rule to clean up old deployments
resource "aws_s3_bucket_lifecycle_configuration" "deployment" {
  bucket = aws_s3_bucket.deployment.id

  rule {
    id     = "cleanup-old-deployments"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    expiration {
      days = 90
    }
  }
}

# Bucket policy to allow EC2 instance access
resource "aws_s3_bucket_policy" "deployment" {
  bucket = aws_s3_bucket.deployment.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowEC2Access"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.eval_server.arn
        }
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.deployment.arn,
          "${aws_s3_bucket.deployment.arn}/*"
        ]
      }
    ]
  })
}

# Results bucket for evaluation outputs
resource "aws_s3_bucket" "results" {
  bucket = "${var.environment}-crucible-results-${data.aws_caller_identity.current.account_id}"
  
  tags = {
    Name        = "Crucible Evaluation Results"
    Environment = var.environment
    Purpose     = "Store evaluation outputs"
  }
}

# Versioning for results bucket
resource "aws_s3_bucket_versioning" "results" {
  bucket = aws_s3_bucket.results.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Encryption for results bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "results" {
  bucket = aws_s3_bucket.results.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access for both buckets
resource "aws_s3_bucket_public_access_block" "deployment" {
  bucket = aws_s3_bucket.deployment.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "results" {
  bucket = aws_s3_bucket.results.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}

# Outputs
output "deployment_bucket_name" {
  value       = aws_s3_bucket.deployment.id
  description = "Name of the deployment S3 bucket"
}

output "deployment_bucket_arn" {
  value       = aws_s3_bucket.deployment.arn
  description = "ARN of the deployment S3 bucket"
}

output "results_bucket_name" {
  value       = aws_s3_bucket.results.id
  description = "Name of the results S3 bucket"
}

output "deployment_command" {
  value       = "aws s3 cp your-package.tar.gz s3://${aws_s3_bucket.deployment.id}/"
  description = "Command to upload deployment packages"
}