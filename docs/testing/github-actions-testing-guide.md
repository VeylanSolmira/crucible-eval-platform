# GitHub Actions Testing Guide

## Overview

This guide explains how testing works in GitHub Actions for the Crucible Platform, including the differences from local testing and strategies for efficient CI/CD.

## How GitHub Actions Testing Works

### Key Concepts

1. **Ephemeral Environments**: Each workflow run gets a fresh Ubuntu VM
2. **No Persistent State**: Everything must be set up from scratch
3. **Resource Constraints**: Limited CPU/memory compared to development machines
4. **Time Limits**: Jobs timeout after 6 hours, workflows after 35 days
5. **Parallel Execution**: Jobs run in parallel, steps run sequentially

### Testing Strategies

#### 1. Local Kubernetes (Small Projects)
```yaml
- uses: helm/kind-action@v1
- run: |
    kubectl apply -k k8s/base
    pytest tests/
```

**Pros**: Fast, isolated, no external dependencies
**Cons**: Limited resources, not production-like

#### 2. External Test Cluster (Enterprise)
```yaml
- run: |
    aws eks update-kubeconfig --name test-cluster
    kubectl create namespace test-${{ github.run_id }}
    kubectl apply -k k8s/overlays/test
```

**Pros**: Production-like, real infrastructure
**Cons**: Costs, cleanup complexity, slower

#### 3. Hybrid Approach (Recommended)
- Unit/Integration tests in GitHub Actions with kind/k3s
- E2E/Performance tests against staging cluster
- Production validation against real infrastructure

## Local vs GitHub Actions Testing

### Local Testing Flow
```bash
# 1. Start cluster (already running)
./start-platform.sh

# 2. Run tests
python tests/test_orchestrator.py unit integration e2e security performance \
  -v --parallel --include-slow
```

### GitHub Actions Flow
```yaml
# 1. Setup infrastructure (every time)
- Setup kubectl, Docker, Python
- Create/connect to cluster
- Build and push images
- Deploy services

# 2. Run tests
- Execute test orchestrator
- Collect results
- Clean up resources
```

## Workflow Architecture

### Option 1: Monolithic Test Job
```yaml
test:
  runs-on: ubuntu-latest
  steps:
    - Setup cluster
    - Deploy services
    - Run all tests
    - Cleanup
```

**Pros**: Simple, sequential
**Cons**: Slow, no parallelization

### Option 2: Parallel Test Jobs (Recommended)
```yaml
setup:
  # Deploy cluster and services
  
unit-tests:
  needs: setup
  # Run unit tests
  
integration-tests:
  needs: setup
  # Run integration tests
  
cleanup:
  needs: [all-tests]
  # Tear down
```

**Pros**: Fast, parallel execution
**Cons**: Complex coordination

### Option 3: Matrix Strategy
```yaml
test:
  strategy:
    matrix:
      suite: [unit, integration, e2e, security, performance]
  steps:
    - Run ${{ matrix.suite }} tests
```

**Pros**: DRY, scalable
**Cons**: Shared setup overhead

## Handling Large Clusters

### Problem
- GitHub Actions runners have limited resources
- Large clusters need external infrastructure
- Tests need production-like environments

### Solutions

1. **Minimal Local Testing**
   ```yaml
   # GitHub Actions: Run core tests with minimal resources
   - run: |
       kind create cluster --config=kind-minimal.yaml
       pytest tests/unit tests/integration -m "not requires_large_cluster"
   ```

2. **Staging Cluster Testing**
   ```yaml
   # Trigger tests on staging infrastructure
   - run: |
       aws lambda invoke --function-name trigger-staging-tests
       # Poll for results
   ```

3. **Progressive Testing**
   - PR: Unit + basic integration
   - Merge to main: Full test suite on staging
   - Release: Performance + chaos tests on prod-like

## Best Practices

### 1. Use Test Namespaces
```yaml
env:
  TEST_NAMESPACE: crucible-test-${{ github.run_id }}
```

### 2. Implement Proper Cleanup
```yaml
cleanup:
  if: always()  # Run even if tests fail
  steps:
    - kubectl delete namespace ${{ env.TEST_NAMESPACE }}
```

### 3. Cache Dependencies
```yaml
- uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
```

### 4. Use Artifacts for Test Results
```yaml
- uses: actions/upload-artifact@v3
  if: always()
  with:
    name: test-results
    path: |
      test-results/
      coverage/
```

### 5. Implement Timeouts
```yaml
- name: Run tests
  timeout-minutes: 30
  run: pytest tests/
```

## Cost Optimization

### For Large Clusters

1. **Schedule-based Testing**
   ```yaml
   on:
     schedule:
       - cron: '0 2 * * *'  # Nightly
   ```

2. **Manual Approval Gates**
   ```yaml
   environment:
     name: staging
     # Requires manual approval
   ```

3. **Resource Quotas**
   ```yaml
   - run: |
       kubectl apply -f - <<EOF
       apiVersion: v1
       kind: ResourceQuota
       metadata:
         name: test-quota
       spec:
         hard:
           requests.cpu: "10"
           requests.memory: "20Gi"
       EOF
   ```

## Implementation Example

Here's how to update your workflow for the hybrid approach:

```yaml
name: Test Suite

on:
  pull_request:
  push:
    branches: [main]

jobs:
  # Quick tests in GitHub Actions
  quick-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup kind cluster
        uses: helm/kind-action@v1
        with:
          cluster_name: crucible-test
          
      - name: Build and load images
        run: |
          docker build -t api-service:test ./api
          kind load docker-image api-service:test
          
      - name: Deploy minimal services
        run: |
          kubectl apply -k k8s/overlays/minimal-test
          
      - name: Run quick tests
        run: |
          python tests/test_orchestrator.py unit integration \
            -v --parallel

  # Full test suite on staging
  staging-tests:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Trigger staging tests
        run: |
          curl -X POST ${{ secrets.STAGING_TEST_WEBHOOK }} \
            -H "Authorization: Bearer ${{ secrets.STAGING_TOKEN }}" \
            -d '{
              "ref": "${{ github.sha }}",
              "suites": ["unit", "integration", "e2e", "security", "performance"],
              "parallel": true,
              "include_slow": true
            }'
          
      - name: Wait for results
        run: |
          # Poll for test completion
          # Download results artifact
```

## Monitoring and Alerts

### Success Notification
```yaml
- name: Notify success
  if: success()
  run: |
    curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
      -d '{"text": "✅ All tests passed for ${{ github.sha }}"}'
```

### Integration Ready Alert
```yaml
- name: Mark as integration-ready
  if: success() && github.ref == 'refs/heads/main'
  run: |
    aws dynamodb put-item \
      --table-name deployment-status \
      --item '{
        "sha": {"S": "${{ github.sha }}"},
        "status": {"S": "integration-ready"},
        "timestamp": {"N": "'$(date +%s)'"}
      }'
```