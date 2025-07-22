# Kubernetes Testing Quickstart

## TL;DR

```bash
# Run all tests in Kubernetes (parallel execution)
python tests/test_orchestrator.py --parallel

# Run specific test suites
python tests/test_orchestrator.py unit integration

# Quick smoke test only
python tests/smoke/run_smoke_tests.py
```

## Architecture Summary

We've built a sophisticated test orchestration system:

1. **Smoke Tests** (`tests/smoke/`) - Verify cluster readiness (5 seconds)
2. **Test Orchestrator** (`tests/test_orchestrator.py`) - Main entry point that:
   - Runs smoke tests
   - Builds test image
   - Submits coordinator job
3. **Test Coordinator** (`tests/coordinator.py`) - Runs in-cluster and:
   - Discovers test suites
   - Creates parallel test jobs
   - Aggregates results

## What We Built vs Original Approach

### Original Approach
- Single job running all tests sequentially
- Simple but slow
- Hard to debug failures

### New Architecture  
- Coordinator + parallel worker jobs
- Each test suite runs independently
- Better visibility and faster execution
- Professional CI/CD pattern

## Next Steps

1. **Build the test image**:
   ```bash
   docker build -f tests/Dockerfile -t crucible-test-runner:latest .
   ```

2. **Try a simple test run**:
   ```bash
   python tests/test_orchestrator.py unit --skip-build
   ```

3. **Update destructive tests** to work with Kubernetes (they currently use Docker commands)

## Key Files

- `tests/test_orchestrator.py` - Main entry point (run this!)
- `tests/smoke/test_cluster_access.py` - Smoke tests
- `tests/coordinator.py` - In-cluster coordinator
- `tests/kubernetes/*.md` - Documentation

## Common Issues

**"kubectl not found"**
- Install kubectl: `brew install kubectl`

**"Smoke tests failing"**  
- Check cluster: `kubectl get pods -n crucible`
- Verify services: `kubectl get svc -n crucible`

**"Image pull errors"**
- Build locally first: `docker build -f tests/Dockerfile -t crucible-test-runner:latest .`
- Or configure ECR_REGISTRY environment variable