# Unit Test Philosophy and Best Practices

## Overview

This document outlines the philosophy behind unit testing, particularly for Kubernetes applications, and discusses the trade-offs between different testing approaches.

## Traditional Unit Testing Philosophy

### Core Principles

1. **Isolation**: Unit tests should test a single unit of code in isolation from external dependencies
2. **Speed**: Tests should run in milliseconds, not seconds
3. **Determinism**: Tests should produce the same result every time
4. **Independence**: Tests should not depend on external services or state
5. **Simplicity**: Tests should be easy to run anywhere (developer laptop, CI, etc.)

### Typical Setup for Kubernetes Applications

For applications that deploy to Kubernetes, the traditional testing pyramid looks like:

```
         /\
        /E2E\        (Run in real cluster)
       /------\
      /  Integ  \    (Run against test cluster)
     /------------\
    /   Unit Tests  \  (Run locally, no cluster needed)
   /------------------\
```

**Unit Tests** (Bottom layer):
- Run with `pytest` or `go test` locally
- Mock all external dependencies (Kubernetes API, databases, etc.)
- No cluster required
- Milliseconds to run
- Run on every code change

**Integration Tests** (Middle layer):
- Run against test services or test cluster
- Test component interactions
- May use real APIs with test data
- Seconds to minutes to run
- Run on PR/merge

**E2E Tests** (Top layer):
- Run in production-like environment
- Test full user workflows
- Use real services
- Minutes to hours to run
- Run before release

## Current Approach: All Tests in Cluster

Our current approach runs all tests (including unit tests) inside the Kubernetes cluster using the test orchestrator.

### Advantages
- **Consistency**: All tests run in the same environment
- **Realistic Environment**: Tests run closer to production conditions
- **Single Infrastructure**: One test setup to maintain
- **Environment Parity**: No "works on my machine" issues

### Disadvantages
- **Slower Feedback**: Must build image, create job, wait for scheduling
- **Resource Intensive**: Requires running cluster even for simple tests
- **Complex Debugging**: Logs are in pods, not local terminal
- **Higher Barrier**: Can't run tests without cluster access

### Example Flow
```bash
# Traditional unit test
$ pytest tests/unit/test_foo.py  # <-- Instant feedback

# Our approach
$ python tests/test_orchestrator.py --test-files unit/test_foo.py
# 1. Build Docker image
# 2. Push to registry
# 3. Create Kubernetes job
# 4. Wait for pod scheduling
# 5. Stream logs back
# Total time: 30-60 seconds vs <1 second
```

## Best Practices for Unit Tests

Regardless of where they run, unit tests should:

### 1. Mock External Dependencies
```python
@patch('dispatcher_service.app.core_v1')
def test_execute_creates_job(mock_k8s_api):
    # Mock the Kubernetes API
    mock_k8s_api.create_namespaced_job.return_value = V1Job(...)
    
    # Test only the dispatcher logic
    response = execute(request)
    assert response.status == "created"
```

### 2. Test Edge Cases
```python
def test_handles_api_timeout():
    mock_api.create_job.side_effect = TimeoutError()
    response = execute(request)
    assert response.status == "error"
```

### 3. Be Fast and Focused
- Each test should test one thing
- No sleep() or wait loops
- Mock time-dependent behavior

### 4. Be Deterministic
- Same input → same output
- No random data without seeding
- No dependency on test order

## Hybrid Approach Considerations

A potential middle ground could be:

1. **Local Unit Tests**: 
   - Pure unit tests that can run locally
   - Fastest feedback for developers
   - No cluster needed

2. **Cluster Component Tests**:
   - Tests that need some real services
   - Run in cluster but still mock some dependencies
   - Balance between isolation and integration

3. **Full Integration Tests**:
   - Test real service interactions
   - Run in cluster with real dependencies

## Recommendations

1. **Keep Mocking in Unit Tests**: Even if running in-cluster, unit tests should mock external dependencies for speed and determinism

2. **Consider Local Execution**: Add support for running unit tests locally for faster developer feedback

3. **Clear Test Categories**: Clearly distinguish between:
   - Pure unit tests (fully mocked)
   - Component tests (some real services)
   - Integration tests (minimal mocking)
   - E2E tests (no mocking)

4. **Document Expectations**: Make it clear which tests require cluster access and why

## Conclusion

While our approach of running all tests in-cluster is unconventional, it has valid benefits. The key is to maintain unit testing best practices (mocking, isolation, speed) even within this infrastructure. Consider adopting a hybrid approach that allows both local and in-cluster execution based on developer needs and test types.