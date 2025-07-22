# Local Kubernetes Deployment Guide

## Prerequisites

1. **Local Kubernetes Cluster** (choose one):
   - [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Kubernetes enabled
   - [Minikube](https://minikube.sigs.k8s.io/docs/start/)
   - [Kind](https://kind.sigs.k8s.io/docs/user/quick-start/)

2. **kubectl** installed and configured

3. **Docker images** built locally or available in registry

## Quick Start

### Option A: Using Skaffold (Recommended)

```bash
# Install Skaffold if you haven't already
# Mac: brew install skaffold
# Linux: curl -Lo skaffold https://storage.googleapis.com/skaffold/releases/latest/skaffold-linux-amd64 && chmod +x skaffold && sudo mv skaffold /usr/local/bin

# One command to build, deploy, and watch for changes
skaffold dev --port-forward

# Or just build and deploy once
skaffold run
```

### Option B: Manual Build and Deploy

```bash
# Build all images
docker compose build

# Tag for local k8s use
docker tag crucible-platform/api-service:local crucible-platform/api-service:latest
docker tag crucible-platform/storage-service:local crucible-platform/storage-service:latest
docker tag crucible-platform/storage-worker:local crucible-platform/storage-worker:latest
docker tag crucible-platform/celery-worker:local crucible-platform/celery-worker:latest
docker tag crucible-platform/dispatcher-service:local crucible-platform/dispatcher-service:latest
docker tag crucible-platform/frontend:local crucible-platform/frontend:latest
```

### 2. Secrets Configuration

For local development, the default passwords in `secrets.yaml` match Docker Compose:
- Database password: `changeme`
- Flower auth: `admin:changeme`

**No changes needed for local development!**

For production, update the secrets:
```bash
# Option 1: Edit the file
cp k8s/base/config/secrets.yaml k8s/base/config/secrets-prod.yaml
# Then edit secrets-prod.yaml with real passwords

# Option 2: Create from environment variables
kubectl create secret generic postgres-secret \
  --from-literal=password=$DB_PASSWORD \
  -n crucible --dry-run=client -o yaml > secrets.yaml
```

### 3. Deploy to Local Kubernetes

```bash
# Create namespace
kubectl create namespace crucible

# Deploy everything
kubectl apply -k k8s/base/

# Wait for pods to be ready
kubectl wait --for=condition=ready pod --all -n crucible --timeout=300s
```

### 4. Run Database Migrations

```bash
# Check if postgres is ready
kubectl get pod -n crucible -l app=postgres

# Run migrations
kubectl create job --from=cronjob/db-migrate db-migrate-manual -n crucible
# OR if using the Job directly:
kubectl apply -f k8s/base/postgres/migration-job.yaml
```

### 5. Access the Application

```bash
# Port forward to access services
kubectl port-forward -n crucible svc/crucible-frontend 3000:3000 &
kubectl port-forward -n crucible svc/api-service 8080:8080 &
kubectl port-forward -n crucible svc/flower-service 5555:5555 &

# Access at:
# - Frontend: http://localhost:3000
# - API: http://localhost:8080
# - Flower: http://localhost:5555 (admin:changeme)
```

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n crucible
kubectl describe pod <pod-name> -n crucible
kubectl logs <pod-name> -n crucible
```

### Common Issues

1. **ImagePullBackOff**
   ```bash
   # For local images with Minikube
   eval $(minikube docker-env)
   # Then rebuild images
   
   # For Kind
   kind load docker-image crucible-platform/api-service:latest
   ```

2. **PVC Pending**
   ```bash
   # Check storage class
   kubectl get storageclass
   # May need to create local storage provisioner
   ```

3. **Database Connection Failed**
   ```bash
   # Check if migration ran
   kubectl logs job/db-migrate -n crucible
   # Check postgres logs
   kubectl logs statefulset/postgres -n crucible
   ```

## Local Development Tips

### Use Skaffold (Recommended)
```yaml
# skaffold.yaml
apiVersion: skaffold/v2beta28
kind: Config
build:
  artifacts:
  - image: crucible-platform/api-service
    docker:
      dockerfile: api/Dockerfile
deploy:
  kubectl:
    manifests:
    - k8s/base/*
```

Then run:
```bash
skaffold dev --port-forward
```

### Direct Pod Updates
```bash
# For quick testing, update image directly
kubectl set image deployment/api-service api-service=crucible-platform/api-service:dev -n crucible
```

### Clean Up
```bash
# Delete everything
kubectl delete namespace crucible

# Or just delete specific resources
kubectl delete -k k8s/base/
```

## ECR Authentication (if using ECR images)

**CRITICAL: This is the CORRECT way to create ECR secret**

```bash
# DO NOT use --docker-password=stdin or --docker-password=-
# Those create secrets with literal passwords "stdin" or "-"

# Correct method:
ECR_PASSWORD=$(aws ecr get-login-password --region us-west-2)
kubectl create secret docker-registry ecr-secret \
  --docker-server=503132503803.dkr.ecr.us-west-2.amazonaws.com \
  --docker-username=AWS \
  --docker-password="$ECR_PASSWORD" \
  -n crucible
```

**To refresh the secret (expires every 12 hours):**
```bash
kubectl delete secret ecr-secret -n crucible
ECR_PASSWORD=$(aws ecr get-login-password --region us-west-2)
kubectl create secret docker-registry ecr-secret \
  --docker-server=503132503803.dkr.ecr.us-west-2.amazonaws.com \
  --docker-username=AWS \
  --docker-password="$ECR_PASSWORD" \
  -n crucible
```

## Differences from Production

1. **No ECR** - Using local Docker images (unless you specifically configure ECR)
2. **No LoadBalancer** - Using NodePort or port-forward
3. **Local Storage** - Using local PVs instead of EBS
4. **Single Node** - No real distribution
5. **No TLS** - HTTP only for local dev
6. **No Docker-in-Docker** - Kind uses containerd, so executors can't create containers
   - This means evaluation execution won't work locally
   - Consider moving to Phase 2 of executor migration (Kubernetes Jobs)
   - Or use Docker Desktop instead of Kind for full functionality

## Next Steps

1. Set up local image registry for faster updates
2. Use Tilt or Skaffold for hot reloading
3. Add local ingress controller (nginx or traefik)
4. Set up local monitoring (Prometheus/Grafana)