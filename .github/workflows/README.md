# GitHub Actions Workflows

This directory contains CI/CD workflows for the METR evaluation platform.

## Active Workflows

### 🏗️ **build-and-push.yml**
**Purpose**: Build and push Docker images to Amazon ECR  
**Triggers**: Manual dispatch or called by other workflows  
**Key Features**:
- Uses `docker-compose.build.yml` with buildx bake
- Builds all images for linux/amd64 platform
- Pushes to separate ECR repositories per service
- Tags images with environment name (dev, staging, production)

**Usage**:
```yaml
# Manual trigger
workflow_dispatch:
  environment: dev  # or staging, production
```

### 📦 **eks-lifecycle.yml**
**Purpose**: Manage EKS cluster lifecycle (pause/resume for cost savings)  
**Triggers**: Manual or scheduled  
**Actions**:
- `pause`: Scale down node groups to 0
- `resume`: Scale up node groups to configured size

### 🔧 **generate-openapi-spec.yml**
**Purpose**: Generate OpenAPI specifications for services  
**Triggers**: Called by build workflows  
**Output**: OpenAPI YAML/JSON files for API and storage service

### 🏗️ **terraform.yml**
**Purpose**: Manage infrastructure with Terraform/OpenTofu  
**Triggers**: Manual dispatch  
**Actions**:
- `plan`: Show what would change
- `apply`: Apply infrastructure changes
- `destroy`: Tear down infrastructure (requires confirmation)

### 🧪 **test-kubernetes-v2.yml**
**Purpose**: Run comprehensive test suites  
**Triggers**: Push to main/develop or manual  
**Test Suites**:
- `unit`: Unit tests
- `integration`: Integration tests
- `e2e`: End-to-end tests
- `security`: Security scans
- `performance`: Performance tests

### 🔒 **privacy-check.yml**
**Purpose**: Check for sensitive files in repository  
**Triggers**: Push to main, PRs  
**Checks**: Warns about interview prep materials, personal notes

## Workflow Dependencies

```
build-and-push.yml
  └── generate-openapi-spec.yml (generates API specs)
```

## Image Tagging Strategy

Images are tagged with environment names:
- `api:dev` - Development environment
- `api:staging` - Staging environment  
- `api:production` - Production environment

Each service has its own ECR repository:
- `503132503803.dkr.ecr.us-west-2.amazonaws.com/api`
- `503132503803.dkr.ecr.us-west-2.amazonaws.com/frontend`
- `503132503803.dkr.ecr.us-west-2.amazonaws.com/storage-service`
- etc.

## Common Usage Patterns

### Build and Push Images
```bash
# Trigger build-and-push workflow
gh workflow run build-and-push.yml -f environment=dev
```

### Manage EKS Cluster
```bash
# Pause cluster (save costs)
gh workflow run eks-lifecycle.yml -f action=pause

# Resume cluster
gh workflow run eks-lifecycle.yml -f action=resume
```

### Run Tests
```bash
# Run all tests
gh workflow run test-kubernetes-v2.yml -f test_suites="unit integration e2e"

# Run specific suite
gh workflow run test-kubernetes-v2.yml -f test_suites=unit
```

## Environment Variables

Workflows use GitHub repository variables:
- `AWS_ROLE_ARN`: IAM role for OIDC authentication
- `AWS_REGION`: Target AWS region (default: us-west-2)

## Authentication

All AWS operations use OIDC (OpenID Connect) for secure, temporary credentials. No long-lived AWS keys are stored in GitHub.

## Archived Workflows

The following workflows have been archived to the `archived/` directory:
- `deploy-compose.yml` - Old Docker Compose deployment (replaced by Kubernetes)
- `deploy-base.yml` - Merged into build-and-push
- `test-kubernetes.yml` - Replaced by v2
- `apply-k8s-manifests.yml` - Will be merged into a unified deploy workflow
- `deploy-dev.yml` - Will be merged into a unified deploy workflow
- `deploy-k8s.yml` - Will be merged into a unified deploy workflow

## Next Steps

1. Create unified `deploy.yml` workflow that:
   - Calls build-and-push if needed
   - Applies Kubernetes manifests
   - Handles all environments (dev, staging, production)

2. Update build-and-push to handle deployment as well (build-deploy pattern)

## Troubleshooting

### Build Failures
- Check OpenAPI spec generation succeeded
- Verify docker-compose.build.yml syntax
- Ensure all required files are present

### ECR Push Failures
- Verify AWS credentials and permissions
- Check ECR repositories exist (created via Terraform)
- Ensure image names match ECR repository names