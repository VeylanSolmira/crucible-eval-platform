# Kubernetes Manifests

This directory contains all Kubernetes deployment configurations for the Crucible Platform.

## Directory Structure

```
k8s/
├── base/           # Kustomize base configurations (if using Kustomize)
├── overlays/       # Environment-specific overrides (dev, staging, prod)
├── frontend/       # Frontend service deployment
├── api/            # API Gateway service
├── storage/        # Storage service
├── redis/          # Redis deployment
├── postgres/       # PostgreSQL deployment  
├── celery/         # Celery workers
├── executors/      # Executor service pods
├── monitoring/     # Prometheus, Grafana, etc.
├── ingress/        # Nginx ingress controller
└── evaluator-pod.yaml  # Legacy - single pod example
```

## Migration Order

Following our [Kubernetes Migration Guide](../docs/kubernetes/migration-guide.md):

1. **Phase 1**: Frontend only (learn basics)
2. **Phase 2**: Add API (service discovery)
3. **Phase 3**: Add Storage + Redis (stateful services)
4. **Phase 4**: Complete migration (all services)

## Quick Start

```bash
# Start with minikube
minikube start

# Deploy frontend first
kubectl apply -f k8s/frontend/

# Check status
kubectl get pods
kubectl get services
```

## Design Decisions

- **Service-based organization**: Each service has its own directory
- **Clear dependencies**: Services deployed in dependency order
- **Environment flexibility**: Use Kustomize overlays for different environments
- **Learning-friendly**: Start simple, add complexity gradually

## Notes

- This is NOT infrastructure code (that's in `/infrastructure`)
- These are application deployment configurations
- Start with local development (minikube/kind) before cloud deployment