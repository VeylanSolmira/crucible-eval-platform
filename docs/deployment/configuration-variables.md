# Deployment Configuration Variables

This document describes all configuration variables used across the deployment pipeline.

## Overview

Instead of hardcoding values like `crucible-platform` throughout our scripts, we use configuration variables that can be set at different levels:

1. **GitHub Repository Variables** - For GitHub Actions workflows
2. **Terraform Variables** - For infrastructure provisioning
3. **Environment Variables** - For local development and Docker

## GitHub Repository Variables

Set these in your GitHub repository settings under Settings → Secrets and variables → Actions → Variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `us-west-2` | AWS region for deployment |
| `PROJECT_NAME` | `crucible-platform` | Project identifier used for tagging and naming |
| `CONTAINER_NAME` | `crucible-platform` | Docker container name |
| `ECR_REPOSITORY` | `crucible-platform` | ECR repository name |
| `AWS_ROLE_ARN` | *(required)* | IAM role for GitHub Actions OIDC |

## Terraform Variables

Defined in `infrastructure/terraform/variables.tf`:

```hcl
variable "project_name" {
  default = "crucible-platform"
}

variable "aws_region" {
  default = "us-west-2"
}

variable "environment" {
  default = "production"
}
```

## Environment Variables

For local development, create a `.env` file based on `.env.deploy`:

```bash
# Core configuration
PROJECT_NAME=crucible-platform
CONTAINER_NAME=crucible-platform
ECR_REPOSITORY=crucible-platform
AWS_REGION=us-west-2

# Derived paths
STORAGE_PATH=/home/ubuntu/storage
LOG_PATH=/var/log/${PROJECT_NAME}
```

## SSM Parameter Paths

All SSM parameters follow the pattern `/${PROJECT_NAME}/parameter-name`:

- `/${PROJECT_NAME}/docker-image` - Current Docker image
- `/${PROJECT_NAME}/deployment-bucket` - S3 deployment bucket name
- `/${PROJECT_NAME}/current-version` - Current deployed version

## Docker Compose

The `docker-compose.yml` file uses environment variable substitution:

```yaml
services:
  crucible-platform:
    image: ${PROJECT_NAME:-crucible-platform}:local
    container_name: ${CONTAINER_NAME:-crucible-platform}
```

## Systemd Service

The systemd service file (`crucible-docker.service`) uses placeholders that are replaced during deployment:

- `${ECR_REPOSITORY_URL}` - Replaced by Terraform
- `${CONTAINER_NAME}` - Replaced by Terraform

## Changing Project Name

To deploy with a different project name:

1. **GitHub Actions**: Set repository variables
2. **Terraform**: Override in `terraform.tfvars`:
   ```hcl
   project_name = "my-project"
   ```
3. **Local Development**: Set in `.env`:
   ```bash
   PROJECT_NAME=my-project
   CONTAINER_NAME=my-project
   ```

## Best Practices

1. **Consistency**: Use the same variable names across all systems
2. **Defaults**: Provide sensible defaults for development
3. **Documentation**: Update this file when adding new variables
4. **Validation**: Test with different values to ensure flexibility

## Migration from Hardcoded Values

We've migrated from hardcoded values to variables in:
- ✅ GitHub Actions workflows
- ✅ Docker Compose files
- ✅ Systemd service templates
- ✅ Terraform configurations
- ✅ SSM parameter paths

This allows for:
- Multiple deployments with different names
- Easy environment separation (dev/staging/prod)
- Consistent naming across all resources
- Simplified configuration management