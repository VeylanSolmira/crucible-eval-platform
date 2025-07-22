# Test Environment Architecture

## Overview

This document outlines the test environment architecture for the Crucible platform, including namespace strategies, RBAC considerations, and deployment patterns for different testing scenarios.

## Environment Types

### 1. Local Development (`crucible` namespace)
- **Overlay**: `k8s/overlays/local/`
- **Purpose**: Day-to-day development and manual testing
- **Characteristics**:
  - Uses main `crucible` namespace
  - Includes test-runner RBAC for convenience
  - Shares resources with development work
  - Quick iteration with Skaffold dev mode

### 2. Test Environment (`crucible-test` namespace)
- **Overlay**: `k8s/overlays/test/`
- **Purpose**: Automated testing, CI/CD pipelines
- **Characteristics**:
  - Isolated `crucible-test` namespace
  - Complete resource duplication
  - Reduced resource requirements
  - Clean environment for each test run

### 3. Production Environment
- **Overlay**: `k8s/overlays/production/`
- **Purpose**: Production deployments
- **Characteristics**:
  - No test infrastructure
  - No test-runner RBAC
  - Production-grade resource allocations
  - Enhanced security policies

## RBAC Security Considerations

### The Security Trade-off
Test runner permissions (ability to list/delete jobs, read pods, etc.) present a potential security vulnerability:
- **Risk**: Compromised test pod could inspect/manipulate cluster resources
- **Mitigation**: Isolate test permissions to non-production environments

### Current Implementation
```yaml
# Local overlay includes test permissions for convenience
k8s/overlays/local/test-runner-rbac.yaml

# Test overlay has dedicated namespace and permissions
k8s/overlays/test/test-runner-rbac.yaml  

# Production overlay has NO test permissions
k8s/overlays/production/  # No test RBAC
```

## Namespace Isolation

When using different namespaces (e.g., `crucible-test`), Kubernetes provides complete isolation:

### What Gets Duplicated
- PostgreSQL database instance
- Redis instances (main + Celery)
- All microservices (API, storage, dispatcher, etc.)
- Persistent volumes
- ConfigMaps and Secrets
- Network policies

### Benefits
- **Complete isolation**: Tests can't affect other environments
- **Parallel testing**: Multiple test suites in different namespaces
- **Clean state**: Each test run starts fresh
- **Safety**: Destructive tests can't impact development/production

### Costs
- **Resource usage**: Multiple copies of entire stack
- **Complexity**: Managing multiple environments
- **Storage**: Each namespace needs its own PVCs

## Skaffold Multi-Environment Strategies

### Option 1: Profiles
```yaml
profiles:
- name: local
  deploy:
    kustomize:
      paths: ["k8s/overlays/local"]
- name: test
  deploy:
    kustomize:
      paths: ["k8s/overlays/test"]
```

Usage: `skaffold dev -p test`

### Option 2: Multiple Instances
```bash
# Terminal 1
skaffold dev --kustomize-paths k8s/overlays/local

# Terminal 2  
skaffold dev --kustomize-paths k8s/overlays/test
```

### Option 3: Multi-Module Configuration
```yaml
apiVersion: skaffold/v4beta6
kind: Config
metadata:
  name: local-env
deploy:
  kustomize:
    paths: ["k8s/overlays/local"]
---
apiVersion: skaffold/v4beta6
kind: Config  
metadata:
  name: test-env
deploy:
  kustomize:
    paths: ["k8s/overlays/test"]
```

Usage: `skaffold dev -m local-env,test-env`

## CI/CD Considerations

### GitHub Actions Workflow
```yaml
- name: Deploy test environment
  run: |
    kubectl apply -k k8s/overlays/test/
    kubectl wait --for=condition=ready pod -l app=api-service -n crucible-test

- name: Run tests
  run: |
    python tests/test_orchestrator.py --namespace crucible-test
```

### Benefits for CI/CD
- **Isolation**: Each PR gets its own namespace
- **Cleanup**: Easy to delete entire namespace after tests
- **Parallel runs**: Multiple PRs can test simultaneously
- **Reproducibility**: Clean environment every time

## Recommendations

### For Local Development
1. Continue using `crucible` namespace with local overlay
2. Keep test-runner RBAC in local overlay for convenience
3. Use Skaffold dev mode for rapid iteration

### For CI/CD
1. Use test overlay deploying to `crucible-test` namespace
2. Create namespace per PR/run for complete isolation
3. Implement automatic cleanup after test completion

### For Production
1. Never include test infrastructure
2. Use separate cluster if possible
3. Implement strict RBAC and network policies

## Future Improvements

### 1. Lightweight Test Mode
Create a minimal test configuration that shares some resources:
- Shared PostgreSQL/Redis between test runs
- Only isolate evaluation pods
- Reduce resource overhead

### 2. Dynamic Namespace Creation
Implement dynamic namespace creation for CI/CD:
```bash
NAMESPACE="crucible-test-pr-${PR_NUMBER}"
kubectl create namespace $NAMESPACE
kubectl apply -k k8s/overlays/test/ -n $NAMESPACE
```

### 3. Test Data Management
- Implement database seeding for consistent test data
- Create snapshot/restore mechanisms
- Version test data with migrations

### 4. Resource Optimization
- Use init containers to check service readiness
- Implement pod priority for test workloads
- Configure resource quotas per namespace

## Security Best Practices

1. **Principle of Least Privilege**: Only grant permissions needed for specific tests
2. **Namespace Isolation**: Always use separate namespaces for test environments
3. **RBAC Auditing**: Regularly review and audit test permissions
4. **Network Policies**: Implement strict network isolation for test pods
5. **Resource Quotas**: Prevent test environments from consuming excessive resources

## Conclusion

The multi-overlay approach provides flexibility for different testing needs while maintaining security. Local development gets convenience, CI/CD gets isolation, and production stays clean. The key is choosing the right approach for each use case and being explicit about security trade-offs.