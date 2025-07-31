# Terraform Bootstrap Module
# This module creates the S3 bucket and DynamoDB table needed for terraform remote state
# Run this ONCE with local state, then use remote state for everything else

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile != "" ? var.aws_profile : null
}

# S3 bucket for terraform state
resource "aws_s3_bucket" "terraform_state" {
  bucket = "${var.project_name}-terraform-state-${data.aws_caller_identity.current.account_id}"

  # Prevent accidental deletion
  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name        = "Terraform State Storage"
    Project     = var.project_name
    Purpose     = "Remote state storage for Terraform"
    Environment = "shared"
    ManagedBy   = "terraform-bootstrap"
  }
}

# Enable versioning for state history
resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block all public access
resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# DynamoDB table for state locking
resource "aws_dynamodb_table" "terraform_state_lock" {
  name         = "${var.project_name}-terraform-state-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name        = "Terraform State Lock"
    Project     = var.project_name
    Purpose     = "Prevent concurrent terraform operations"
    Environment = "shared"
    ManagedBy   = "terraform-bootstrap"
  }
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}

# Outputs for main terraform configuration
output "s3_bucket_name" {
  description = "Name of the S3 bucket for terraform state"
  value       = aws_s3_bucket.terraform_state.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket for terraform state"
  value       = aws_s3_bucket.terraform_state.arn
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table for state locking"
  value       = aws_dynamodb_table.terraform_state_lock.id
}

output "backend_config" {
  description = "Backend configuration for terraform"
  value = {
    bucket         = aws_s3_bucket.terraform_state.id
    key            = "${var.project_name}/terraform.tfstate"
    region         = var.aws_region
    dynamodb_table = aws_dynamodb_table.terraform_state_lock.id
    encrypt        = true
  }
}

# Generate backend configuration file
resource "local_file" "backend_config" {
  filename = "${path.module}/backend-config.hcl"
  content  = <<-EOT
    bucket         = "${aws_s3_bucket.terraform_state.id}"
    key            = "${var.project_name}/terraform.tfstate"
    region         = "${var.aws_region}"
    dynamodb_table = "${aws_dynamodb_table.terraform_state_lock.id}"
    encrypt        = true
  EOT
}

# Instructions for using the backend
output "usage_instructions" {
  description = "Instructions for using the terraform backend"
  value       = <<-EOT
    
    Terraform Backend Setup Complete!
    
    1. Copy the backend configuration to your main terraform:
       
       terraform {
         backend "s3" {
           bucket         = "${aws_s3_bucket.terraform_state.id}"
           key            = "${var.project_name}/terraform.tfstate"
           region         = "${var.aws_region}"
           dynamodb_table = "${aws_dynamodb_table.terraform_state_lock.id}"
           encrypt        = true
         }
       }
    
    2. Initialize your main terraform with:
       terraform init -backend-config=../terraform-bootstrap/backend-config.hcl
    
    3. For GitHub Actions, the backend will use the IAM role automatically.
    
    4. For local development, terraform will use your AWS profile.
    
    IMPORTANT: This bootstrap module should continue using local state.
    Do NOT add a backend configuration to this module!
  EOT
}