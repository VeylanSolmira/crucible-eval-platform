# Kustomize - Configuration Management Without Templates

## What is Kustomize?

Kustomize is a Kubernetes-native configuration management tool that lets you customize raw YAML files without using templates. It's been built into kubectl since v1.14, so you might already have it!

```bash
# Check if you have it
kubectl kustomize --help
```

## The Problem It Solves

### Without Kustomize (Copy-Paste Approach)
```
k8s/
├── frontend-dev.yaml      # 90% duplicate code
├── frontend-staging.yaml  # 90% duplicate code
├── frontend-prod.yaml     # 90% duplicate code
```

### With Kustomize (Base + Patches)
```
k8s/
├── base/
│   └── frontend.yaml           # Single source of truth
└── overlays/
    ├── dev/
    │   └── kustomization.yaml  # Just the differences
    ├── staging/
    │   └── kustomization.yaml  # Just the differences
    └── prod/
        └── kustomization.yaml  # Just the differences
```

## How It Works

### 1. Base Configuration
`k8s/base/frontend.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: frontend
        image: frontend:latest
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
```

`k8s/base/kustomization.yaml`:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
- frontend.yaml
- service.yaml
```

### 2. Environment Overlays

`k8s/overlays/prod/kustomization.yaml`:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

bases:
- ../../base

# Change replica count
replicas:
- name: frontend
  count: 3

# Update image tag
images:
- name: frontend
  newTag: v2.0.0

# Patch resources
patches:
- target:
    kind: Deployment
    name: frontend
  patch: |-
    - op: replace
      path: /spec/template/spec/containers/0/resources/requests/memory
      value: "512Mi"
```

### 3. Apply Configuration
```bash
# Preview what will be generated
kubectl kustomize k8s/overlays/prod/

# Apply directly
kubectl apply -k k8s/overlays/prod/

# Or generate and apply
kustomize build k8s/overlays/prod/ | kubectl apply -f -
```

## Key Features

### 1. **Resource Generators**
```yaml
# Generate ConfigMaps from files
configMapGenerator:
- name: app-config
  files:
  - application.properties

# Generate Secrets
secretGenerator:
- name: app-secret
  literals:
  - password=mypassword
```

### 2. **Common Labels/Annotations**
```yaml
commonLabels:
  app: crucible
  environment: production

commonAnnotations:
  managed-by: kustomize
```

### 3. **Name Prefixes/Suffixes**
```yaml
namePrefix: prod-
nameSuffix: -v2
```

### 4. **Strategic Merge Patches**
```yaml
patches:
- path: increase-memory.yaml
  target:
    group: apps
    version: v1
    kind: Deployment
```

## Benefits

1. **No Templates** - Work with plain Kubernetes YAML
2. **DRY Principle** - Don't repeat yourself
3. **Git-Friendly** - See exactly what changes per environment
4. **Built into kubectl** - No extra tools needed
5. **Declarative** - Describe desired state, not generation process
6. **Reusable** - Share bases across projects

## Kustomize vs Helm

| Feature | Kustomize | Helm |
|---------|-----------|------|
| Approach | Overlays/Patches | Templates |
| Learning Curve | Lower | Higher |
| Built into kubectl | Yes | No |
| Package Distribution | No | Yes |
| Complex Logic | Limited | Full templating |
| Use Case | Env variations | App distribution |

## When to Use Kustomize

### ✅ Good For:
- Managing dev/staging/prod variations
- Keeping YAML DRY across environments
- Teams already using plain YAML
- Simple customizations

### ❌ Consider Helm For:
- Distributing apps to others
- Complex templating logic
- Package management needs
- Conditional resource creation

## Example: Multi-Environment Setup

```
k8s/
├── base/
│   ├── kustomization.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── configmap.yaml
└── overlays/
    ├── development/
    │   ├── kustomization.yaml
    │   ├── replica-count.yaml    # 1 replica
    │   └── resource-limits.yaml  # Low limits
    ├── staging/
    │   ├── kustomization.yaml
    │   ├── replica-count.yaml    # 2 replicas
    │   └── resource-limits.yaml  # Medium limits
    └── production/
        ├── kustomization.yaml
        ├── replica-count.yaml    # 3 replicas
        ├── resource-limits.yaml  # High limits
        └── pdb.yaml             # Pod disruption budget
```

## For Your Project

I noticed you already have a Kustomize structure:
- `/k8s/base/` - Base configurations
- `/k8s/overlays/` - Environment-specific overlays

However, for initial Kubernetes learning, I recommend:
1. Start with plain YAML files
2. Understand core Kubernetes concepts
3. Add Kustomize when you need multiple environments
4. It's already there when you need it!

## Quick Commands

```bash
# Build and view output
kubectl kustomize k8s/overlays/dev/

# Apply directly
kubectl apply -k k8s/overlays/dev/

# Delete resources
kubectl delete -k k8s/overlays/dev/

# Validate structure
kubectl kustomize k8s/base/
```

Kustomize is powerful for maintaining DRY Kubernetes configs without the complexity of templating!