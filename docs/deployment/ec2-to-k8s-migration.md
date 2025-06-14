# Migration Guide: EC2 to Kubernetes

## Current State
- Python app deployed to EC2 via userdata
- Systemd managing the service
- S3 or GitHub for code deployment

## Target State
- Containerized app running on EKS
- Kubernetes managing lifecycle
- Container registry (ECR) for deployments

## Migration Steps

### Step 1: Containerize (Do This Now)

```bash
# Build and test locally
docker build -t crucible-platform:latest .

# Run with docker-compose
docker-compose up -d

# Verify it works
curl http://localhost:8080/health
```

### Step 2: Update CI/CD (Next Sprint)

```yaml
# .github/workflows/build.yml
name: Build and Push
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        role-to-assume: arn:aws:iam::123456789:role/github-actions
        aws-region: us-west-2
    
    - name: Login to ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1
    
    - name: Build and push
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        IMAGE_TAG: ${{ github.sha }}
      run: |
        docker build -t $ECR_REGISTRY/crucible-platform:$IMAGE_TAG .
        docker push $ECR_REGISTRY/crucible-platform:$IMAGE_TAG
```

### Step 3: Deploy to EKS (Future)

1. Update Terraform to create EKS cluster
2. Apply K8s manifests
3. Set up monitoring
4. Migrate traffic

## Benefits of Container Approach for METR

1. **Security**: 
   - Immutable containers
   - No SSH access needed
   - Read-only filesystems
   - Network isolation

2. **Scalability**:
   - Horizontal pod autoscaling
   - Multiple evaluations in parallel
   - Resource isolation per evaluation

3. **Reliability**:
   - Health checks and auto-restart
   - Rolling updates
   - Easy rollbacks

4. **Observability**:
   - Centralized logging
   - Prometheus metrics
   - Distributed tracing

## Quick Test: Run Container on EC2

You can test the container approach on your existing EC2:

```bash
# On your EC2 instance
cd /home/ubuntu/crucible

# Build container
docker build -t crucible-platform:latest .

# Stop systemd service
sudo systemctl stop crucible-platform

# Run as container
docker run -d \
  --name crucible \
  --restart unless-stopped \
  -p 8080:8080 \
  -v $(pwd)/storage:/app/storage \
  --security-opt no-new-privileges:true \
  --read-only \
  --tmpfs /tmp \
  crucible-platform:latest

# Check logs
docker logs -f crucible
```

## Timeline Recommendation

1. **Week 1**: Get Docker working locally
2. **Week 2**: Update EC2 to run containers
3. **Week 3**: Set up ECR and CI/CD
4. **Week 4**: Create EKS cluster
5. **Week 5**: Deploy to Kubernetes
6. **Week 6**: Add security features (gVisor, network policies)

This gradual approach lets you learn and test each component while maintaining a working system.