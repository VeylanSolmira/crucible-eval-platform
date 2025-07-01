# Testing Strategy

## Overview

We follow the Testing Pyramid approach, balancing test speed, reliability, and confidence. The pyramid ensures we have many fast unit tests, fewer integration tests, and minimal (but critical) end-to-end tests.

## Testing Pyramid

```
        /\
       /E2E\      (10%)
      /------\
     /  Integ \   (20%)
    /----------\
   /    Unit    \ (70%)
  /--------------\
```

## 1. Unit Tests (70%)

### Purpose
- Test individual functions/classes in isolation
- Verify business logic correctness
- Document expected behavior
- Enable refactoring with confidence

### Characteristics
- **Fast**: Run in milliseconds
- **Isolated**: No external dependencies (mocked)
- **Deterministic**: Same input = same output
- **Focused**: Test one thing at a time

### Example: Celery Task Cancellation
```python
@patch('api.app.celery_client.celery_app')
def test_cancel_pending_task(mock_celery_app):
    """Test cancelling a pending task."""
    # Mock the Celery components
    mock_result = Mock()
    mock_result.state = 'PENDING'
    mock_result.revoke = Mock()
    
    # Test the logic
    result = cancel_celery_task('test-123')
    
    # Verify behavior
    assert result['cancelled'] is True
    mock_result.revoke.assert_called_once()
```

### When to Use
- Testing business logic
- Testing error handling
- Testing edge cases
- Testing data transformations

### Benefits
- Run thousands in seconds
- Easy to debug failures
- Can run anywhere (CI, local)
- No infrastructure needed

## 2. Integration Tests (20%)

### Purpose
- Test component interactions
- Verify configuration correctness
- Test with real external services
- Catch integration issues

### Characteristics
- **Slower**: Seconds to minutes
- **Real Dependencies**: Actual Redis, databases, etc.
- **Environment-Specific**: Need proper setup
- **Broader Scope**: Test multiple components

### Example: Celery with Real Redis
```python
def test_task_cancellation_with_real_celery():
    """Test cancellation with real Celery broker."""
    # Submit real task to Celery
    task = evaluate_code.delay('test-123', 'print("hello")')
    
    # Cancel it
    task.revoke()
    
    # Verify it's actually cancelled in Redis
    assert task.state == 'REVOKED'
```

### When to Use
- Testing database queries
- Testing message queue interactions
- Testing API client behavior
- Testing caching logic

### Setup Requirements
```yaml
# docker-compose.test.yml
services:
  redis:
    image: redis:7
  celery-broker:
    image: rabbitmq:3
  postgres:
    image: postgres:15
```

## 3. End-to-End Tests (10%)

### Purpose
- Test complete user workflows
- Verify system behavior as a whole
- Catch deployment/configuration issues
- Ensure critical paths work

### Characteristics
- **Slowest**: Minutes per test
- **Full Stack**: Everything running
- **Flaky**: Network, timing issues
- **Expensive**: Resource intensive

### Example: Complete Evaluation Flow
```python
def test_full_evaluation_workflow():
    """Test submitting code and getting results."""
    # Start with API call
    response = client.post('/api/eval', json={
        'code': 'print("Hello, World!")',
        'language': 'python'
    })
    eval_id = response.json()['eval_id']
    
    # Poll for completion
    wait_for_completion(eval_id, timeout=30)
    
    # Verify results
    result = client.get(f'/api/eval/{eval_id}')
    assert result.json()['output'] == 'Hello, World!\n'
```

### When to Use
- Critical user journeys
- Deployment verification
- Performance testing
- Security testing

## Testing Best Practices

### 1. Test Naming
```python
# Good
def test_cancel_pending_task_returns_success():
def test_cancel_completed_task_returns_error():

# Bad
def test_cancel():
def test_1():
```

### 2. Arrange-Act-Assert
```python
def test_example():
    # Arrange - Set up test data
    task_id = 'test-123'
    mock_celery = create_mock_celery()
    
    # Act - Execute the behavior
    result = cancel_task(task_id)
    
    # Assert - Verify the outcome
    assert result['success'] is True
```

### 3. One Assertion Per Test
```python
# Good - Focused tests
def test_dlq_adds_task_to_queue():
    dlq.add_task(task)
    assert dlq.size() == 1

def test_dlq_sets_task_metadata():
    dlq.add_task(task)
    assert dlq.get_task(task.id).status == 'failed'

# Bad - Multiple assertions
def test_dlq():
    dlq.add_task(task)
    assert dlq.size() == 1
    assert dlq.get_task(task.id).status == 'failed'
    assert dlq.statistics()['total'] == 1
```

### 4. Mock External Dependencies
```python
@patch('requests.get')
def test_api_call(mock_get):
    # Control external behavior
    mock_get.return_value.json.return_value = {'status': 'ok'}
    
    # Test your code
    result = check_health()
    assert result == 'healthy'
```

## Testing Infrastructure

### Continuous Integration
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pytest tests/unit -v --cov

  integration-tests:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7
    steps:
      - uses: actions/checkout@v3
      - run: pytest tests/integration -v

  e2e-tests:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - run: docker-compose up -d
      - run: pytest tests/e2e -v
```

### Local Development
```bash
# Run all tests
make test

# Run only unit tests (fast)
make test-unit

# Run with coverage
make test-coverage

# Run specific test
pytest tests/unit/test_celery.py::test_cancel_task -v
```

## Coverage Goals

### Unit Test Coverage
- **Target**: 80-90%
- **Focus**: Business logic, error paths
- **Exclude**: Simple getters/setters, config

### Integration Test Coverage
- **Target**: Critical paths covered
- **Focus**: External service interactions
- **Exclude**: Third-party library internals

### E2E Test Coverage
- **Target**: Happy paths + critical errors
- **Focus**: User-facing features
- **Exclude**: Admin/debug endpoints

## Common Testing Patterns

### 1. Fixtures for Reusable Setup
```python
@pytest.fixture
def celery_app():
    """Provide configured Celery app."""
    app = Celery('test')
    app.conf.update(CELERY_ALWAYS_EAGER=True)
    return app

def test_task_execution(celery_app):
    result = my_task.delay()
    assert result.successful()
```

### 2. Parameterized Tests
```python
@pytest.mark.parametrize("state,expected", [
    ('PENDING', True),
    ('SUCCESS', False),
    ('FAILURE', False),
    ('REVOKED', False),
])
def test_can_cancel_task(state, expected):
    task = create_task_with_state(state)
    assert can_cancel(task) == expected
```

### 3. Testing Async Code
```python
@pytest.mark.asyncio
async def test_async_evaluation():
    result = await evaluate_code_async('print("test")')
    assert result['status'] == 'completed'
```

## Anti-Patterns to Avoid

### 1. Testing Implementation Details
```python
# Bad - Tests internal method calls
def test_bad():
    obj._internal_method = Mock()
    obj.public_method()
    obj._internal_method.assert_called()

# Good - Tests behavior
def test_good():
    result = obj.public_method()
    assert result == expected_value
```

### 2. Excessive Mocking
```python
# Bad - Mocking too much
@patch('module.func1')
@patch('module.func2')
@patch('module.func3')
@patch('module.func4')
def test_too_many_mocks(...):
    # Hard to understand what's being tested

# Good - Minimal mocking
@patch('external_api.call')
def test_focused(mock_api):
    # Clear what's mocked and why
```

### 3. Time-Dependent Tests
```python
# Bad - Depends on wall clock
def test_bad():
    start = datetime.now()
    do_something()
    assert datetime.now() - start < 1

# Good - Control time
@freeze_time("2024-01-01")
def test_good():
    result = get_timestamp()
    assert result == "2024-01-01"
```

## Testing Tools

### Python
- **pytest**: Test runner with fixtures
- **pytest-mock**: Better mocking
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting
- **factory-boy**: Test data generation
- **freezegun**: Time mocking

### JavaScript/TypeScript
- **Jest**: Test runner and mocking
- **React Testing Library**: Component testing
- **MSW**: Mock Service Worker for APIs
- **Cypress**: E2E testing

### Infrastructure
- **Testcontainers**: Disposable test environments
- **LocalStack**: Mock AWS services
- **WireMock**: HTTP API mocking

## Debugging Failed Tests

### 1. Verbose Output
```bash
pytest -vv -s tests/failing_test.py
```

### 2. Drop into Debugger
```python
def test_debug():
    import pdb; pdb.set_trace()
    # Execution stops here
```

### 3. Print Actual vs Expected
```python
def test_comparison():
    actual = function_under_test()
    expected = {'status': 'ok'}
    assert actual == expected, f"Got {actual}, expected {expected}"
```

### 4. Capture Logs
```python
def test_with_logs(caplog):
    with caplog.at_level(logging.DEBUG):
        function_that_logs()
    assert "Expected message" in caplog.text
```

## Interview Questions

### Common Testing Questions
1. **"How do you decide what to test?"**
   - Critical business logic first
   - Error paths and edge cases
   - External integrations
   - Anything that has broken before

2. **"How do you handle flaky tests?"**
   - Identify root cause (timing, external deps)
   - Add retries for E2E tests only
   - Mock external services in unit tests
   - Use explicit waits, not sleep()

3. **"What's your approach to test data?"**
   - Factories for complex objects
   - Fixtures for common scenarios
   - Random data for property tests
   - Separate test database

4. **"How do you test microservices?"**
   - Contract testing between services
   - Consumer-driven contracts
   - Service virtualization
   - Distributed tracing in tests