# Executor Image Versioning Issue

## Problem
The dispatcher service needs to create Kubernetes Jobs with executor images, but there's a versioning mismatch:

1. **Static Services**: Use kustomize to set image tags (e.g., `api:dev`, `api:sha-abc123`)
2. **Dynamic Jobs**: Dispatcher creates Jobs at runtime and needs to know which executor tag to use
3. **Version Drift**: The executor images could have different tags than the dispatcher itself

## Current Workaround
In dev environment, we set `DEFAULT_IMAGE_TAG=dev` via kustomization patch. This works but is not ideal because:
- It's a fixed tag that doesn't update with deployments
- Doesn't work for SHA-based production deployments
- Breaks if someone forgets to push executor images with matching tag

## Proper Solutions

### 1. Tag Inheritance
Dispatcher uses its own image tag for executor images:
```python
# Dispatcher running as: dispatcher:sha-abc123
# Creates jobs with: executor-ml:sha-abc123
```

### 2. ConfigMap Generation
Kustomize generates the executor ConfigMap with current tags:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
configMapGenerator:
- name: executor-images
  files:
  - images.yaml
  replacements:
  - source:
      kind: Image
      name: executor-ml
    targets:
    - select:
        name: executor-images
      fieldPaths:
      - data.images.yaml
```

### 3. Version API
Add endpoint to query available executor versions:
```python
GET /api/executors/executor-ml/versions
{
  "latest": "sha-abc123",
  "versions": ["sha-abc123", "sha-def456", "v1.2.3"]
}
```

### 4. Deployment Metadata
Pass deployment version as environment variable:
```yaml
env:
- name: DEPLOYMENT_VERSION
  value: "sha-abc123"  # Set by CI/CD
```

## Recommendation
For production, implement **Tag Inheritance** as it:
- Ensures executor version matches deployment
- Works with any tagging scheme (SHA, semver, etc.)
- No additional configuration needed
- Natural fit for GitOps workflows