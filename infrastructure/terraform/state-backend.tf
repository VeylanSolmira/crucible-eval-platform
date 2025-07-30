# State Backend Resources
# These need to be created before using the remote backend
# Run this first with local state, then migrate

# S3 bucket for terraform state (already exists)
data "aws_s3_bucket" "terraform_state" {
  bucket = "crucible-platform-terraform-state-503132503803"
}

# DynamoDB table for state locking
resource "aws_dynamodb_table" "terraform_state_lock" {
  name         = "crucible-platform-terraform-state-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name        = "Terraform State Lock"
    Environment = var.environment
    Purpose     = "Prevent concurrent terraform operations"
  }
}

# Output the backend configuration for reference
output "terraform_backend_config" {
  description = "Terraform backend configuration"
  value = {
    bucket         = data.aws_s3_bucket.terraform_state.id
    dynamodb_table = aws_dynamodb_table.terraform_state_lock.id
    region         = var.aws_region
    key_prefix     = "crucible-platform"
  }
}