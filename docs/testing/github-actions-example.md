# GitHub Actions Testing Example

## What Happens When You Push Code

Here's a step-by-step walkthrough of what happens when you push code to GitHub:

### 1. Trigger
```bash
git push origin feature/my-feature
```

### 2. GitHub Actions Starts
- GitHub allocates a fresh Ubuntu VM
- No Docker images exist
- No Kubernetes cluster exists
- No Python packages installed

### 3. Workflow Execution

#### For Pull Requests (Using kind)
```
┌─────────────────────────────────────────┐
│ 1. Setup Environment (5-10 min)         │
├─────────────────────────────────────────┤
│ - Install kind, kubectl, skaffold      │
│ - Create local Kubernetes cluster      │
│ - Build all Docker images              │
│ - Load images into kind                │
│ - Deploy services to cluster           │
│ - Wait for all pods to be ready       │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ 2. Run Tests (10-30 min)                │
├─────────────────────────────────────────┤
│ - Setup Python environment             │
│ - Install dependencies                 │
│ - Configure test environment vars      │
│ - Run: python tests/test_orchestrator.py│
│   unit integration e2e security        │
│   performance -v --parallel            │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ 3. Cleanup (1 min)                      │
├─────────────────────────────────────────┤
│ - Delete kind cluster                  │
│ - Upload test results                  │
│ - VM is destroyed                      │
└─────────────────────────────────────────┘
```

#### For Main Branch (Using EKS)
```
┌─────────────────────────────────────────┐
│ 1. Connect to Test Cluster (2 min)      │
├─────────────────────────────────────────┤
│ - Configure AWS credentials            │
│ - Update kubeconfig                    │
│ - Create isolated namespace            │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ 2. Deploy to Test Namespace (5-10 min)  │
├─────────────────────────────────────────┤
│ - Build and push images to ECR         │
│ - Deploy services with skaffold        │
│ - Wait for deployments                 │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ 3. Run Full Test Suite (20-40 min)     │
├─────────────────────────────────────────┤
│ - All tests including slow ones        │
│ - Performance benchmarks               │
│ - Security scanning                    │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ 4. Staging Validation (Optional)        │
├─────────────────────────────────────────┤
│ - Trigger full staging tests           │
│ - Update deployment status             │
│ - Send notifications                   │
└─────────────────────────────────────────┘
```

## Key Differences from Local Testing

### Local Development
```bash
# Cluster already running
# Images already built
# Just run tests immediately
python tests/test_orchestrator.py unit integration e2e security performance -v --parallel
```
**Time**: 5-15 minutes

### GitHub Actions
```yaml
# Must create everything from scratch
# Build all images
# Deploy entire platform
# Then run tests
```
**Time**: 20-50 minutes

## Cost Considerations

### Pull Requests
- Uses GitHub-hosted runners (free for public repos)
- Creates temporary kind cluster (no cloud costs)
- Total cost: $0

### Main Branch
- Uses GitHub-hosted runners
- Deploys to EKS test cluster
- Costs:
  - EKS cluster: ~$0.10/hour
  - EC2 nodes: ~$0.50-2.00/hour depending on size
  - ECR storage: ~$0.10/GB/month
  - Data transfer: ~$0.09/GB

### Example Monthly Costs
```
Assumptions:
- 100 PR builds/month (free)
- 50 main branch builds/month
- 30 minutes per build
- 2 m5.large nodes

Monthly cost:
- EKS: 25 hours × $0.10 = $2.50
- EC2: 25 hours × $0.192 × 2 = $9.60
- ECR: 50GB × $0.10 = $5.00
- Total: ~$17.10/month
```

## Optimization Strategies

### 1. Cache Everything
```yaml
- uses: actions/cache@v3
  with:
    path: |
      ~/.cache/pip
      ~/.docker
      ~/.skaffold
```

### 2. Parallel Jobs
```yaml
strategy:
  matrix:
    test-suite: [unit, integration, e2e]
```

### 3. Conditional Testing
```yaml
# Only run expensive tests on main
if: github.ref == 'refs/heads/main'
```

### 4. Fail Fast
```yaml
strategy:
  fail-fast: true  # Stop all jobs if one fails
```

### 5. Time Limits
```yaml
timeout-minutes: 30  # Prevent runaway jobs
```

## Debugging Failed Tests

### 1. Check Logs
- Click on the failed job
- Expand the failed step
- Look for error messages

### 2. Download Artifacts
```yaml
- uses: actions/download-artifact@v3
  with:
    name: test-results
```

### 3. Re-run with Debug
```yaml
- name: Debug info
  if: failure()
  run: |
    kubectl get all -n $NAMESPACE
    kubectl describe pods -n $NAMESPACE
    kubectl logs -n $NAMESPACE -l app=api-service
```

### 4. SSH into Runner (GitHub Enterprise)
```yaml
- name: Setup tmate session
  if: ${{ failure() }}
  uses: mxschmitt/action-tmate@v3
```

## Common Issues and Solutions

### Issue: Tests timeout
**Solution**: Increase timeout or optimize slow tests
```yaml
timeout-minutes: 60
```

### Issue: Out of memory
**Solution**: Use larger runners or reduce parallelism
```yaml
runs-on: ubuntu-latest-8-cores
```

### Issue: Flaky tests
**Solution**: Add retries or fix race conditions
```yaml
pytest --reruns 3 --reruns-delay 5
```

### Issue: Can't connect to services
**Solution**: Check service readiness and port forwarding
```yaml
kubectl wait --for=condition=ready pod -l app=api-service
kubectl port-forward svc/api-service 8080:8080 &
```