# GitHub Actions Workflows

This directory contains CI/CD workflows for building, testing, and deploying the METR evaluation platform.

## Workflow Overview

### Core Workflows

#### 🏗️ **build-and-push.yml**
Builds all Docker images and pushes them to Amazon ECR.
- Triggers: Called by deployment workflows
- Outputs: Image tag (git SHA) for deployments
- Services built: nginx, api, frontend, executor-service, executor-ml, celery-worker, storage-service, storage-worker

#### 🚀 **deploy-k8s.yml**
Full deployment pipeline to Kubernetes clusters.
- Triggers: Manual (`workflow_dispatch`)
- Options:
  - `environment`: development, staging, or production
  - `skip-build`: Skip building images (use existing)
  - `image-tag`: Specific tag when skipping build
- Flow: Build images → Apply K8s manifests

#### 📋 **apply-k8s-manifests.yml**
Applies Kubernetes manifests without building images.
- Triggers: Manual or called by deploy-k8s.yml
- Use case: Quick config changes, testing manifests
- Inputs:
  - `image-tag`: Which ECR images to use
  - `namespace`: K8s namespace (default: crucible)

#### 🐳 **deploy-compose.yml**
Deploys to EC2 instances using Docker Compose.
- Triggers: Push to main or manual
- Options:
  - `deployment_color`: blue or green deployment
- Flow: Build images → Deploy to tagged EC2 instances

### Utility Workflows

#### 🔧 **deploy-base.yml**
Shared utilities for deployment workflows.
- Not run directly (called by other workflows)
- Handles: AWS auth, ECR registry lookup, image URL retrieval

#### 📜 **generate-openapi-spec.yml**
Generates OpenAPI specifications from Python services.
- Triggers: Called by build workflows
- Creates: API documentation for each service

#### 🔒 **privacy-check.yml**
Checks for sensitive files in the repository.
- Triggers: Push to main, PRs
- Purpose: Warns about interview prep materials, personal notes

### Testing Workflows

#### 🧪 **test-frontend.yml**
Runs frontend tests and linting.
- Triggers: Push, PRs affecting frontend/
- Tests: Jest, ESLint, TypeScript checks

#### 🐍 **test-backend.yml**
Runs backend Python tests.
- Triggers: Push, PRs affecting Python code
- Tests: pytest, mypy, ruff

### Terraform Workflows

#### 🏗️ **terraform-plan.yml**
Plans infrastructure changes.
- Triggers: PRs affecting infrastructure/
- Shows: What would change without applying

#### ✅ **terraform-apply.yml**
Applies infrastructure changes.
- Triggers: Manual only (safety)
- Requires: Review of plan output first

## Common Usage Patterns

### Deploy New Code to Kubernetes
```yaml
# Run deploy-k8s.yml with:
environment: production
skip-build: false  # Build fresh images
```

### Quick K8s Config Change
```yaml
# Run apply-k8s-manifests.yml with:
image-tag: latest  # Use existing images
namespace: crucible
```

### Deploy to Docker Compose (Blue/Green)
```yaml
# Run deploy-compose.yml with:
deployment_color: green  # or blue
```

### Just Build Images
```yaml
# Run build-and-push.yml directly
environment: development
```

## Environment Variables

Workflows use GitHub repository variables:
- `AWS_ROLE_ARN`: IAM role for OIDC authentication
- `AWS_REGION`: Target region (default: us-west-2)
- `PROJECT_NAME`: Project identifier (default: crucible-platform)
- `ECR_REPOSITORY`: ECR repo name
- `DEFAULT_DEPLOYMENT_TARGET`: Default color for compose deployments

## Authentication

All AWS operations use OIDC (OpenID Connect) for secure, temporary credentials. No long-lived AWS keys are stored in GitHub.

## Image Tagging Strategy

- **Build tag**: Git SHA (e.g., `frontend-abc123def`)
- **Environment tags**: `frontend-production`, `frontend-development`
- **Latest tag**: `frontend-latest` (always points to most recent build)

## Deployment Targets

### Kubernetes
- Manifests in `k8s/` directory
- Namespace: `crucible`
- Image substitution: Replaces local image refs with ECR URLs

### Docker Compose
- Blue/Green deployments on EC2
- Systemd service: `crucible-compose.service`
- Deployment via AWS Systems Manager (SSM)

## Troubleshooting

### Workflow Fails at AWS Auth
- Check `AWS_ROLE_ARN` is set in repository variables
- Verify OIDC provider exists in AWS account

### K8s Deployment Can't Find Cluster
- Ensure kubeconfig is stored in SSM Parameter Store:
  ```bash
  aws ssm put-parameter \
    --name "/crucible-platform/k8s-kubeconfig" \
    --value file://~/.kube/config \
    --type SecureString
  ```

### Docker Compose Can't Find Instances
- Check EC2 instances have correct tags:
  - `Project`: crucible-platform
  - `DeploymentColor`: blue or green

## Best Practices

1. **Always test in development first**
2. **Use skip-build for config-only changes**
3. **Review terraform plan before applying**
4. **Monitor deployment status in Actions tab**
5. **Check pod logs if K8s deployment fails**