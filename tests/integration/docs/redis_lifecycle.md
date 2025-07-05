# Redis State Lifecycle Integration Test

This test suite verifies that Redis state is properly managed throughout the evaluation lifecycle.

## Overview

The `test_redis_state_lifecycle.py` test ensures that:

1. **Pending State**: When an evaluation is submitted, a pending key is created in Redis
2. **Running State**: When evaluation starts executing:
   - Running info is stored with executor details
   - Evaluation ID is added to the `running_evaluations` set
3. **Cleanup**: When evaluation completes (success/failure/timeout):
   - Running info is deleted
   - Evaluation is removed from running set
   - All temporary keys are cleaned up

## Test Cases

### 1. `test_successful_evaluation_redis_lifecycle`
- Submits a simple evaluation that succeeds
- Verifies pending → running → completed state transitions
- Ensures all Redis keys are cleaned up after success

### 2. `test_failed_evaluation_redis_lifecycle`
- Submits code that exits with error code
- Verifies Redis state is cleaned up even on failure
- Ensures no orphaned keys remain

### 3. `test_timeout_evaluation_redis_cleanup`
- Submits code that runs longer than timeout
- Verifies timeout handling cleans up Redis properly
- Tests edge case of forced termination

### 4. `test_concurrent_evaluations_redis_tracking`
- Submits multiple evaluations simultaneously
- Verifies Redis correctly tracks all running evaluations
- Ensures cleanup works with concurrent operations

## Running the Tests

### Prerequisites

1. **Services Running**: Ensure the platform is running:
   ```bash
   docker-compose up -d
   ```

2. **Redis Access**: Tests need access to Redis on localhost:6379

3. **API Access**: Tests need access to API on localhost:8000

### Install Test Dependencies

```bash
pip install -r tests/requirements-test.txt
```

### Run All Redis Lifecycle Tests

```bash
# From project root
pytest tests/integration/test_redis_state_lifecycle.py -v

# With detailed output
pytest tests/integration/test_redis_state_lifecycle.py -v -s

# Run specific test
pytest tests/integration/test_redis_state_lifecycle.py::TestRedisStateLifecycle::test_successful_evaluation_redis_lifecycle -v
```

### Run with Custom Configuration

```bash
# Custom API URL
API_BASE_URL=http://myapi:8080/api pytest tests/integration/test_redis_state_lifecycle.py

# Custom Redis URL
REDIS_URL=redis://myredis:6379 pytest tests/integration/test_redis_state_lifecycle.py
```

## Understanding the Output

The test provides detailed logging:

```
INFO:__main__:Submitted evaluation: eval_20240115_120000_abc123
INFO:__main__:Initial Redis state: {'pending': 'queued', 'running_info': None, ...}
INFO:__main__:Running state observed: {'executor_id': 'executor-1', 'container_id': 'abc123', ...}
INFO:__main__:Evaluation eval_20240115_120000_abc123 status: running
INFO:__main__:Evaluation eval_20240115_120000_abc123 status: completed
INFO:__main__:Final Redis state (cleaned): {'pending': None, 'running_info': None, ...}
```

## Redis Keys Monitored

The test monitors these Redis keys:

- `pending:{eval_id}` - Temporary key set when evaluation is queued
- `eval:{eval_id}:running` - Running state information (executor, container, etc.)
- `running_evaluations` - Set containing all currently running evaluation IDs
- `logs:{eval_id}:latest` - Latest log output (if any)

## Debugging Failed Tests

### Check Redis State Manually

```bash
# Connect to Redis
redis-cli

# Check running evaluations
SMEMBERS running_evaluations

# Check specific evaluation
GET eval:your_eval_id:running

# List all keys for an evaluation
KEYS *your_eval_id*
```

### Common Issues

1. **Services Not Ready**
   - Solution: Wait for all services to be healthy
   - The test includes a service readiness check

2. **Redis Connection Failed**
   - Check Redis is running: `docker-compose ps redis`
   - Verify Redis URL is correct

3. **Timing Issues**
   - The test includes appropriate delays for state transitions
   - Increase delays if running on slower systems

4. **Cleanup Failed**
   - The test includes automatic cleanup
   - Manual cleanup: `redis-cli FLUSHDB` (warning: clears all data)

## Integration with CI/CD

Add to your CI pipeline:

```yaml
- name: Run Redis State Tests
  run: |
    docker-compose up -d
    sleep 10  # Wait for services
    pytest tests/integration/test_redis_state_lifecycle.py -v
  env:
    API_BASE_URL: http://localhost:8000/api
    REDIS_URL: redis://localhost:6379
```

## Extending the Tests

To add new Redis state tests:

1. Add test method to `TestRedisStateLifecycle` class
2. Use `redis_verifier` fixture for Redis operations
3. Use `api_client` fixture for API calls
4. Follow the pattern: submit → verify states → wait → verify cleanup

Example:
```python
def test_custom_redis_scenario(self, api_client, redis_verifier):
    # Submit evaluation
    response = api_client.post(...)
    eval_id = response.json()["eval_id"]
    
    # Verify Redis state
    state = redis_verifier.get_all_eval_keys(eval_id)
    assert state["some_key"] == expected_value
    
    # Wait and verify cleanup
    # ...
```