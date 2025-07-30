# Terraform Remote State Configuration
# This ensures all terraform runs (local and GitHub Actions) use the same state

terraform {
  backend "s3" {
    bucket = "crucible-platform-terraform-state-503132503803"
    key    = "crucible-platform/terraform.tfstate"
    region = "us-west-2"

    # Enable state locking with DynamoDB
    dynamodb_table = "crucible-platform-terraform-state-lock"

    # Encrypt state file
    encrypt = true

    # These will be set via backend config or environment variables
    # profile = "your-aws-profile" # for local development
    # role_arn = "arn:aws:iam::503132503803:role/terraform-state-role" # for CI/CD
  }
}