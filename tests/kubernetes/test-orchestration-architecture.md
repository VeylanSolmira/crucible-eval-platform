# Test Orchestration Architecture

## Overview

The test orchestration system provides a sophisticated way to run tests in Kubernetes with parallel execution and proper result aggregation.

## Components

### 1. Test Orchestrator (Local)
- **File**: `test_orchestrator.py`
- **Runs**: On developer's machine or CI runner
- **Responsibilities**:
  - Run smoke tests to verify cluster readiness
  - Build and push test runner Docker image
  - Submit coordinator job to cluster
  - Monitor overall execution

### 2. Test Coordinator (In-Cluster)
- **File**: `tests/coordinator.py`
- **Runs**: As a Kubernetes Job inside the cluster
- **Responsibilities**:
  - Discover available test suites
  - Create individual test jobs for each suite
  - Monitor job execution (parallel or sequential)
  - Aggregate results

### 3. Test Runner Jobs (In-Cluster)
- **Image**: `crucible-test-runner:latest`
- **Runs**: As individual Kubernetes Jobs
- **Responsibilities**:
  - Execute pytest for specific test suite
  - Direct access to cluster services
  - Output results in JUnit format

## Execution Flow

```
┌──────────────────────┐
│   Developer/CI       │
│                      │
│ $ python test_       │
│   orchestrator.py    │
│   unit integration   │
│   --parallel         │
└──────────┬───────────┘
           │
           ▼
    ┌──────────────┐
    │ Smoke Tests  │ ─── FAIL ──→ Exit
    └──────┬───────┘
           │ PASS
           ▼
    ┌──────────────┐
    │ Build Image  │
    │ & Push to    │
    │ Registry     │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │Submit        │     ┌─────────────────────────────┐
    │Coordinator   │────▶│   Kubernetes Cluster         │
    │Job           │     │                             │
    └──────┬───────┘     │  ┌───────────────────┐     │
           │             │  │ Coordinator Job   │     │
           ▼             │  │                   │     │
    ┌──────────────┐     │  │ 1. Discover tests │     │
    │Monitor Logs  │◀────│  │ 2. Submit jobs    │     │
    │& Results     │     │  │ 3. Monitor        │     │
    └──────────────┘     │  └─────────┬─────────┘     │
                         │            │               │
                         │            ▼               │
                         │   ┌────────┴────────┐     │
                         │   │                 │     │
                         │ ┌─▼──┐ ┌─▼──┐ ┌─▼──┐   │
                         │ │Unit│ │API │ │E2E │   │
                         │ │Job │ │Job │ │Job │   │
                         │ └────┘ └────┘ └────┘   │
                         │                         │
                         └─────────────────────────┘
```

## Parallel Execution

When `--parallel` is specified:

1. **Parallel-safe suites** run concurrently:
   - Unit tests
   - Integration tests  
   - Security tests

2. **Non-parallel-safe suites** run sequentially after:
   - E2E tests (may conflict)
   - Performance tests (resource intensive)

## Configuration

### Environment Variables
- `K8S_NAMESPACE` - Target namespace (default: crucible)
- `ECR_REGISTRY` - Docker registry for test images
- `TEST_IMAGE` - Override test runner image

### RBAC Requirements

The coordinator needs permissions to:
```yaml
- Create/delete Jobs
- List/watch Pods
- Get Pod logs
```

## Usage Examples

```bash
# Run all tests
python test_orchestrator.py

# Run specific suites in parallel
python test_orchestrator.py unit integration --parallel

# Include slow tests
python test_orchestrator.py --include-slow

# Skip image rebuild
python test_orchestrator.py --skip-build

# Run destructive tests (in isolated namespace)
python test_orchestrator.py --include-destructive
```

## Benefits

1. **Scalability**: Tests run in parallel across cluster nodes
2. **Isolation**: Each test suite gets its own job/pod
3. **Visibility**: Individual logs for each test suite
4. **Flexibility**: Easy to add new test suites
5. **CI/CD Ready**: Same flow works in automation

## Future Enhancements

1. **Result Storage**: Save test results to S3/database
2. **Retry Logic**: Automatic retry of flaky tests
3. **Resource Optimization**: Dynamic resource allocation based on suite
4. **Test Sharding**: Split large suites across multiple jobs
5. **Destructive Test Isolation**: Automatic namespace creation for destructive tests