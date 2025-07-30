# Terraform Bootstrap Module

This module creates the infrastructure needed for Terraform remote state storage:
- S3 bucket for state files
- DynamoDB table for state locking

## Why a Separate Bootstrap Module?

This solves the "chicken and egg" problem:
- Terraform needs a backend to store state
- But we want to manage that backend with Terraform
- Solution: Use a separate module with local state just for the backend

## Usage

### First Time Setup

1. **Delete the manually created bucket** (if it exists):
   ```bash
   aws s3 rb s3://crucible-platform-terraform-state-503132503803 --force
   ```

2. **Initialize and apply this bootstrap module**:
   ```bash
   cd infrastructure/terraform-bootstrap
   terraform init
   terraform apply
   ```

3. **Note the outputs** - they contain the backend configuration

4. **Update the main terraform backend** with the values from the output

5. **Initialize the main terraform** with remote state:
   ```bash
   cd ../terraform
   terraform init -backend-config=../terraform-bootstrap/backend-config.hcl
   ```

### Important Notes

- **This module uses LOCAL state** - the .tfstate file is committed to git
- **Never add a backend to this module** - it must remain local
- **Protect these resources** - they have `prevent_destroy = true`
- **One-time setup** - only run when setting up a new environment

### For CI/CD

GitHub Actions will automatically use the remote backend once configured.
No additional setup needed - it uses IAM roles for authentication.

### For Local Development

Your local AWS credentials will be used automatically.
The same backend is shared between local and CI/CD.