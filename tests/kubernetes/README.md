# Kubernetes Testing Strategy

## Overview

Our testing approach follows a progressive strategy:

1. **Smoke Tests** (Outside cluster) → Verify basic connectivity
2. **Integration Tests** (Inside cluster) → Test service interactions  
3. **Destructive Tests** (Isolated namespace) → Test failure scenarios

## Architecture

```
┌─────────────────────┐
│   Local Machine     │
│                     │
│ 1. Run smoke tests  │──────┐
│ 2. Build test image │      │
│ 3. Submit test jobs │      │
└─────────────────────┘      │
                             v
┌─────────────────────────────────────────────┐
│          Kubernetes Cluster                  │
│                                              │
│  ┌─────────────────────────────────────┐    │
│  │     crucible namespace               │    │
│  │                                      │    │
│  │  • API, Redis, Postgres, etc.       │    │
│  │  • Test Runner Jobs (read-only)     │    │
│  │  • Non-destructive tests            │    │
│  └─────────────────────────────────────┘    │
│                                              │
│  ┌─────────────────────────────────────┐    │
│  │  crucible-test-destructive namespace│    │
│  │                                      │    │
│  │  • Minimal services for testing     │    │
│  │  • Destructive test jobs           │    │
│  │  • Can delete/restart services     │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

## Test Execution Flow

### 1. Smoke Tests (5 seconds)
```bash
# Run from local machine
python tests/smoke/run_smoke_tests.py

# Verifies:
# - kubectl connectivity
# - Services are running
# - Can create jobs
```

### 2. Main Test Suite (5-10 minutes)
```bash
# Run tests inside cluster
python tests/run_in_cluster.py

# Or specific suites:
python tests/run_in_cluster.py integration
python tests/run_in_cluster.py unit
```

### 3. Destructive Tests (When needed)
```bash
# Run with special flag
python tests/run_in_cluster.py --destructive
```

## Key Design Decisions

### Why Run Tests Inside the Cluster?

1. **Realistic Environment** - Tests see actual network topology
2. **No Port Forwarding** - Direct service access
3. **Scalable** - Can run parallel test jobs
4. **Cloud-Native** - Same pattern works in CI/CD

### Why NOT Clone All Resources?

- **Performance**: Reusing existing services is faster
- **Cost**: No duplicate databases/caches
- **Simplicity**: Less to manage and clean up
- **Realistic**: Tests run against actual services

### When to Use Test Namespaces?

**Use Main Namespace For:**
- Unit tests
- Integration tests  
- API tests
- Performance tests

**Use Isolated Namespace For:**
- Killing services
- Network partition tests
- Resource exhaustion tests
- Chaos engineering

## Test Runner Image

The test runner image (`tests/Dockerfile`) contains:
- Python 3.11
- All test dependencies
- Test code
- Pytest configuration

Built and pushed to registry before running tests:
```bash
docker build -f tests/Dockerfile -t crucible-test-runner:latest .
docker push <registry>/crucible-test-runner:latest
```

## Configuration

### Environment Variables
- `K8S_NAMESPACE` - Target namespace (default: crucible)
- `TEST_RUNNER_IMAGE` - Test image location
- `IN_CLUSTER_TESTS=true` - Set inside cluster

### Service Account Permissions

**Read-Only (Default)**:
```yaml
- pods: get, list
- services: get, list
- jobs: get, list
```

**Destructive Tests**:
```yaml
- pods: get, list, delete
- deployments: get, list, patch
```

## Local Development Workflow

```bash
# 1. Verify cluster is ready
python tests/smoke/run_smoke_tests.py

# 2. Build test image (if changed)
docker build -f tests/Dockerfile -t crucible-test-runner:latest .

# 3. Run tests in cluster
python tests/run_in_cluster.py

# 4. Check specific test locally (with port-forward)
kubectl port-forward svc/api-service 8080:8080 &
pytest tests/integration/test_api.py -v
```

## CI/CD Workflow

See `.github/workflows/test-kubernetes.yml` for automated testing:
1. Creates test namespace
2. Deploys services
3. Runs smoke tests
4. Runs integration tests as Jobs
5. Cleans up

## Debugging Failed Tests

```bash
# List test jobs
kubectl get jobs -l app=test-runner

# Get logs from failed test
kubectl logs job/integration-tests-20240716-143022

# Debug pod directly
kubectl run debug --rm -it --image=crucible-test-runner:latest -- bash
```

## Best Practices

1. **Mark Tests Appropriately**
   ```python
   @pytest.mark.destructive  # Requires isolated namespace
   @pytest.mark.slow         # Takes > 30 seconds
   ```

2. **Use Fixtures for Setup**
   ```python
   @pytest.fixture
   def test_namespace():
       # Create isolated namespace
       yield namespace
       # Cleanup
   ```

3. **Stream Logs for Visibility**
   - Always use `kubectl logs -f` for real-time feedback
   - Capture exit codes for CI/CD integration

4. **Clean Up After Tests**
   - Delete test jobs after completion
   - Remove test namespaces
   - Use `--wait=false` for faster cleanup