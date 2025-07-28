# GitOps Development Workflow

## Overview

This document describes the recommended development workflow using a persistent Kubernetes cluster with GitOps principles.

## Architecture

```
Developer Machine          GitHub              AWS
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   Code      │────▶│  Repository     │────▶│  GitHub Actions  │
│   Changes   │     │                 │     │                  │
└─────────────┘     └─────────────────┘     └────────┬─────────┘
                                                      │
                                                      ▼
                                             ┌──────────────────┐
                                             │      ECR         │
                                             │  Image Registry  │
                                             └────────┬─────────┘
                                                      │
                                                      ▼
                                             ┌──────────────────┐
                                             │   EKS Cluster    │
                                             │  ┌────────────┐  │
                                             │  │    Dev     │  │
                                             │  │ Namespace  │  │
                                             │  ├────────────┤  │
                                             │  │  Staging   │  │
                                             │  │ Namespace  │  │
                                             │  ├────────────┤  │
                                             │  │Production  │  │
                                             │  │ Namespace  │  │
                                             │  └────────────┘  │
                                             └──────────────────┘
```

## Development Workflow

### 1. Initial Setup (One Time)

```bash
# Create EKS cluster
eksctl create cluster \
  --name crucible-platform \
  --region us-west-2 \
  --nodegroup-name workers \
  --node-type t3.xlarge \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 5 \
  --managed

# Create namespaces
kubectl create namespace dev
kubectl create namespace staging
kubectl create namespace production

# Install cluster essentials
kubectl apply -f k8s/cluster-essentials/
```

### 2. Daily Development Flow

#### Local Development
```bash
# 1. Make code changes
vim api/microservices_gateway.py

# 2. Test locally (optional)
docker-compose up

# 3. Commit and push
git add .
git commit -m "feat: Add new endpoint"
git push origin feature/my-feature
```

#### Automatic Deployment
```yaml
# .github/workflows/deploy-dev.yml
on:
  push:
    branches: [feature/*, develop]

jobs:
  deploy:
    steps:
      - Build and push to ECR
      - Deploy to dev namespace
      - Run smoke tests
      - Notify Slack
```

#### Remote Development with Skaffold
```bash
# Connect to remote cluster
aws eks update-kubeconfig --name crucible-platform

# Use Skaffold for hot reload
skaffold dev --namespace=dev --default-repo=$ECR_REGISTRY

# Changes are automatically synced to cluster
```

### 3. Testing Production Features

#### Horizontal Pod Autoscaling (HPA)
```yaml
# Deploy HPA in dev namespace
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-service-hpa
  namespace: dev
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

```bash
# Test HPA behavior
# Generate load
kubectl run -i --tty load-generator --rm --image=busybox --restart=Never -- \
  /bin/sh -c "while sleep 0.01; do wget -q -O- http://api-service.dev/api/health; done"

# Watch HPA scale
kubectl get hpa -n dev -w
```

#### Network Policies
```yaml
# Test network isolation
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-ingress
  namespace: dev
spec:
  podSelector:
    matchLabels:
      app: api-service
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: dev
    - podSelector:
        matchLabels:
          app: frontend
```

#### Resource Limits and Requests
```yaml
# Test resource constraints
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### 4. Environment Promotion

```bash
# After testing in dev
git checkout main
git merge feature/my-feature
git push origin main

# Automatic deployment pipeline:
# main → staging namespace → run full tests → production namespace
```

## Benefits of This Approach

### 1. **Real Production Testing**
- Test actual Kubernetes features (HPA, PDB, Network Policies)
- Real resource constraints and limits
- Actual service mesh behavior
- True multi-tenancy

### 2. **Faster Development**
- No cluster startup time
- Immediate feedback
- Hot reload with Skaffold
- Shared development environment

### 3. **Cost Effective**
```
Monthly costs (estimate):
- EKS Control Plane: $73
- 3x t3.xlarge nodes: ~$380
- Load Balancer: ~$25
- Total: ~$478/month

Compared to:
- Developer time saved: 2-3 hours/day
- At $100/hour: $4,000-6,000/month value
```

### 4. **Production Parity**
- Same cluster type (EKS)
- Same networking (VPC, Security Groups)
- Same IAM roles and policies
- Same monitoring and logging

## Implementation Steps

### Phase 1: Infrastructure (Week 1)
- [ ] Create EKS cluster with Terraform
- [ ] Set up VPC with proper subnets
- [ ] Configure IAM roles (IRSA)
- [ ] Install cluster essentials (ingress, cert-manager, etc.)

### Phase 2: CI/CD (Week 2)
- [ ] GitHub Actions for ECR builds
- [ ] ArgoCD for GitOps deployments
- [ ] Automated testing in dev namespace
- [ ] Promotion pipeline (dev → staging → prod)

### Phase 3: Developer Experience (Week 3)
- [ ] Developer onboarding docs
- [ ] Skaffold profiles for each namespace
- [ ] kubectl aliases and tools
- [ ] Monitoring dashboards

### Phase 4: Production Features (Week 4)
- [ ] HPA configurations
- [ ] PodDisruptionBudgets
- [ ] Network Policies
- [ ] Resource Quotas
- [ ] Cluster Autoscaling

## Tools and Configuration

### Required Tools
```bash
# Install required tools
brew install kubectl aws-cli helm skaffold k9s

# Configure AWS CLI
aws configure

# Install eksctl
brew tap weaveworks/tap
brew install weaveworks/tap/eksctl
```

### Skaffold Configuration
```yaml
# skaffold.yaml
apiVersion: skaffold/v2beta29
kind: Config
metadata:
  name: crucible-platform
build:
  artifacts:
  - image: api-service
    context: api
  - image: storage-service
    context: storage
deploy:
  kubectl:
    manifests:
    - k8s/base/*
    - k8s/overlays/dev/*
profiles:
- name: staging
  deploy:
    kubectl:
      manifests:
      - k8s/base/*
      - k8s/overlays/staging/*
- name: production
  deploy:
    kubectl:
      manifests:
      - k8s/base/*
      - k8s/overlays/production/*
```

### GitHub Actions Workflow
```yaml
name: Deploy to Dev
on:
  push:
    branches: [feature/*, develop]

env:
  ECR_REGISTRY: ${{ vars.ECR_REGISTRY }}
  EKS_CLUSTER: crucible-platform
  
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Configure AWS
      uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: ${{ vars.AWS_ROLE_ARN }}
        aws-region: us-west-2
    
    - name: Login to ECR
      uses: aws-actions/amazon-ecr-login@v2
    
    - name: Build and push
      run: |
        skaffold build --default-repo=$ECR_REGISTRY --tag=$GITHUB_SHA
    
    - name: Deploy to dev
      run: |
        aws eks update-kubeconfig --name $EKS_CLUSTER
        skaffold deploy --namespace=dev --images=$(skaffold build --dry-run --output='{{json .}}' --quiet | jq -r '.builds[].tag' | tr '\n' ',')
    
    - name: Run smoke tests
      run: |
        kubectl wait --for=condition=available deployment/api-service -n dev
        curl -f http://api.dev.crucible-platform.com/health
```

## Best Practices

### 1. **Namespace Isolation**
- Each environment in separate namespace
- Resource quotas per namespace
- Network policies for isolation
- RBAC for access control

### 2. **Resource Management**
```yaml
# Namespace resource quota
apiVersion: v1
kind: ResourceQuota
metadata:
  name: dev-quota
  namespace: dev
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    persistentvolumeclaims: "10"
```

### 3. **Monitoring**
- Prometheus for metrics
- Grafana for dashboards
- CloudWatch for logs
- X-Ray for tracing

### 4. **Security**
- Pod Security Standards
- Network Policies
- IRSA for AWS access
- Secrets management with Sealed Secrets

## Troubleshooting

### Can't connect to cluster
```bash
aws eks update-kubeconfig --name crucible-platform --region us-west-2
kubectl config current-context
```

### Deployment stuck
```bash
kubectl describe deployment api-service -n dev
kubectl logs -l app=api-service -n dev --tail=100
```

### Out of resources
```bash
kubectl top nodes
kubectl describe resourcequota -n dev
```

## Next Steps

1. **Set up EKS cluster** with proper node groups
2. **Configure GitHub Actions** for automated deployments  
3. **Install development tools** (Skaffold, k9s, etc.)
4. **Create namespace structure** with proper RBAC
5. **Start developing** with hot reload!