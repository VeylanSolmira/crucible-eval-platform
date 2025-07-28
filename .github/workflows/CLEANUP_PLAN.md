# Workflow Cleanup Plan

## Current State (12 workflows - too many!)
- apply-k8s-manifests.yml
- build-and-push.yml
- deploy-base.yml
- deploy-compose.yml (DEPRECATED - uses old Docker Compose)
- deploy-dev.yml
- deploy-k8s.yml
- eks-lifecycle.yml
- generate-openapi-spec.yml
- privacy-check.yml
- terraform.yml
- test-kubernetes.yml
- test-kubernetes-v2.yml

## Proposed Structure (5 workflows)

### 1. `build-deploy.yml` (Main workflow)
- Builds Docker images using docker-compose.build.yml
- Pushes to ECR with proper repository structure
- Deploys to Kubernetes (dev/staging/prod)
- Combines: build-and-push, deploy-k8s, deploy-dev

### 2. `infrastructure.yml`
- Terraform/OpenTofu operations
- EKS lifecycle management
- Combines: terraform, eks-lifecycle

### 3. `test.yml`
- All testing (unit, integration, e2e)
- Combines: test-kubernetes, test-kubernetes-v2

### 4. `utils.yml`
- OpenAPI generation
- Other utilities
- Based on: generate-openapi-spec

### 5. `privacy-check.yml`
- Keep as-is (simple and focused)

## Files to Delete
- deploy-compose.yml (old Docker Compose approach)
- deploy-compose.yml.bak
- deploy-base.yml (merge into build-deploy)
- apply-k8s-manifests.yml (merge into build-deploy)
- test-kubernetes.yml (keep v2)
- deploy-dev.yml (merge into build-deploy)
- deploy-k8s.yml (merge into build-deploy)