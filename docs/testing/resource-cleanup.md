# Test Resource Cleanup

This document describes the resource cleanup system for tests, which helps ensure tests run in a clean environment and prevents resource exhaustion during test runs.

## Overview

The resource cleanup system allows tests to automatically clean up Kubernetes resources (pods and jobs) between test executions. This is particularly important for:

1. **Integration tests** - Prevent resource buildup from multiple evaluation runs
2. **Load tests** - Ensure each test starts with known resource availability
3. **Debugging** - Preserve job logs while cleaning up pods

## Usage

### Command Line

When running tests with the test orchestrator, use the `--resource-cleanup` flag:

```bash
# No cleanup (default)
./tests/test_orchestrator.py integration

# Clean up pods only (recommended for most tests)
./tests/test_orchestrator.py integration --resource-cleanup pods

# Clean up both pods and jobs (for load tests)
./tests/test_orchestrator.py integration --resource-cleanup all
```

### In Test Code

Tests can use the `resource_manager` fixture or decorators:

```python
# Using the fixture
def test_evaluation(api_session, resource_manager):
    # Submit evaluation
    eval_id = submit_evaluation(api_session, code="print('test')")
    
    # Track the resource for cleanup
    resource_manager.track_resource("jobs", f"evaluation-job-{eval_id}")
    
    # Test continues...
    # Resources are cleaned up automatically after test

# Using the decorator
from tests.utils.resource_manager import with_resource_cleanup

@with_resource_cleanup(cleanup_level="pods", wait_after=5)
def test_concurrent_evaluations():
    # Test code here
    # Pods cleaned up after test completes

# Using context manager
from tests.utils.resource_manager import managed_test_resources

def test_with_context():
    with managed_test_resources("my_test", cleanup_level="all"):
        # Test code here
        # Resources cleaned up when context exits
```

## Cleanup Levels

### `none` (default)
- No cleanup performed
- Use for debugging or when you need to inspect resources after tests

### `pods`
- Deletes pods but preserves jobs
- Recommended for most tests
- Allows access to job logs via `kubectl logs job/...`
- Frees up memory and CPU resources

### `all`
- Deletes both pods and jobs
- Use for load tests or when job history isn't needed
- Provides maximum resource cleanup

## How It Works

1. **Test Execution**: Each test suite runs in a Kubernetes job
2. **Resource Tracking**: The resource manager tracks created resources
3. **Cleanup Decision**: Based on the cleanup level and test result:
   - Failed tests: Resources preserved for debugging (unless forced)
   - Passed tests: Resources cleaned based on level
4. **Wait Period**: Optional wait after cleanup to ensure resources are freed

## Best Practices

1. **Default to `pods` cleanup** for integration tests:
   ```bash
   ./tests/test_orchestrator.py integration --resource-cleanup pods
   ```

2. **Use `all` cleanup** for load tests:
   ```bash
   ./tests/test_orchestrator.py load --resource-cleanup all
   ```

3. **Track resources explicitly** in tests that create many resources:
   ```python
   for i in range(100):
       eval_id = submit_evaluation(...)
       resource_manager.track_resource("jobs", f"job-{eval_id}")
   ```

4. **Add wait time** for tests sensitive to resource availability:
   ```python
   @with_resource_cleanup(cleanup_level="pods", wait_after=10)
   def test_resource_intensive():
       # Waits 10 seconds after cleanup before next test
   ```

## Troubleshooting

### Tests Still Failing Due to Resources

1. Check current resource usage:
   ```bash
   kubectl get resourcequota evaluation-quota -n crucible
   ```

2. Manually clean up if needed:
   ```bash
   kubectl delete pods -n crucible -l app=evaluation
   kubectl delete jobs -n crucible -l app=evaluation
   ```

3. Increase cleanup level:
   ```bash
   # If using 'pods', try 'all'
   ./tests/test_orchestrator.py --resource-cleanup all
   ```

### Debugging Failed Tests

When tests fail with resource cleanup enabled:

1. Resources are preserved by default for failed tests
2. Access logs:
   ```bash
   kubectl logs job/evaluation-job-xxx -n crucible
   ```
3. Force cleanup after debugging:
   ```bash
   kubectl delete job evaluation-job-xxx -n crucible
   ```

## Integration with CI/CD

For CI/CD pipelines, always use resource cleanup:

```yaml
# GitHub Actions example
- name: Run Integration Tests
  run: |
    ./tests/test_orchestrator.py integration \
      --resource-cleanup pods \
      --parallel
```

## Performance Impact

- **Cleanup time**: 1-5 seconds per test file
- **Wait time**: Configurable (default 3 seconds)
- **Overall impact**: Minimal, prevents resource exhaustion

The cleanup system ensures tests run reliably even on resource-constrained clusters while preserving debugging capabilities.