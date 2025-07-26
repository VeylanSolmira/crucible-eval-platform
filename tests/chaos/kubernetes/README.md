# Kubernetes Chaos Tests

## ⚠️ WARNING

These tests are **DESTRUCTIVE** and will delete pods, scale services, and disrupt your Kubernetes cluster. Only run them in test environments!

## Overview

These chaos tests verify the Crucible platform's resilience to common Kubernetes failures:

- Pod deletions
- Service scaling events  
- Multiple component failures
- Rapid failure cycles

## Test Scenarios

### 1. API Pod Deletion (`test_api_pod_deletion_during_submission`)
- Submits an evaluation
- Deletes the API pod during processing
- Verifies evaluation still completes

### 2. Dispatcher Scaling (`test_dispatcher_failure_during_processing`)
- Submits multiple evaluations
- Scales dispatcher to 0 replicas
- Scales back up
- Verifies evaluations complete

### 3. Storage Worker Deletion (`test_storage_worker_pod_deletion`)
- Submits evaluation
- Deletes storage worker pod
- Verifies data persistence and completion

### 4. Multiple Failures (`test_multiple_component_failures`)
- Submits high-priority evaluation
- Deletes celery worker pod
- Scales down storage worker
- Verifies system recovery

### 5. Rapid Pod Cycling (`test_rapid_pod_cycling`)
- Submits multiple evaluations
- Rapidly deletes pods across components
- Verifies acceptable completion rate

## Running the Tests

### Prerequisites

1. Kubernetes cluster with Crucible platform deployed
2. `kubectl` configured with appropriate access
3. Python with pytest and kubernetes client:
   ```bash
   pip install pytest pytest-asyncio kubernetes requests
   ```

### Execution

Run all chaos tests:
```bash
pytest -m destructive tests/chaos/kubernetes/
```

Run specific test:
```bash
pytest -m destructive tests/chaos/kubernetes/test_pod_resilience.py::test_api_pod_deletion_during_submission -v
```

### Safety Features

- Tests check cluster health before running
- Automatic deployment restoration after each test
- Skip if deployments aren't healthy
- Namespace isolation (only affects specified namespace)

## Configuration

Edit these constants in `test_pod_resilience.py`:

```python
NAMESPACE = "crucible"  # Target namespace
API_SERVICE = "api-service"  # Service names
DISPATCHER_SERVICE = "dispatcher"
```

## Integration with CI/CD

These tests should NOT run automatically in CI/CD pipelines. Instead:

1. Create a separate "chaos testing" workflow
2. Require manual approval
3. Run against dedicated test environment
4. Monitor and alert on failures

## Future Enhancements

When ready for more sophisticated chaos:

1. **Network Chaos** (requires Chaos Mesh)
   - Inject latency between services
   - Simulate network partitions
   - Packet loss scenarios

2. **Resource Chaos**
   - CPU stress on nodes
   - Memory pressure
   - Disk I/O limitations

3. **Time Chaos**
   - Clock skew testing
   - Timezone issues

See [Kubernetes Chaos Testing Guide](../../../docs/testing/kubernetes-chaos-testing.md) for tool recommendations.