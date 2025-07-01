# Tests Directory

Comprehensive test suite for the Crucible platform covering unit, integration, and end-to-end testing.

## Test Organization

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_task_queue.py  # Queue service logic tests
│   ├── test_executor.py    # Executor service tests
│   └── test_storage.py     # Storage layer tests
├── integration/            # Integration tests between services
│   ├── test_api_integration.py
│   ├── test_celery_integration.py
│   └── test_queue_executor_integration.py
├── e2e/                    # End-to-end tests
│   └── test_full_evaluation_flow.py
├── load/                   # Load and performance tests
│   └── test_concurrent_evaluations.py
├── security/               # Security-focused tests
│   ├── test_code_injection.py
│   └── test_container_isolation.py
├── manual/                 # Manual testing scripts
│   ├── README.md
│   └── test-evaluation.sh
├── fixtures/              # Test data and fixtures
│   ├── code_samples/
│   └── mock_responses/
└── conftest.py           # Pytest configuration and shared fixtures
```

## Running Tests

### All Tests
```bash
# From project root
pytest tests/

# With coverage
pytest tests/ --cov=. --cov-report=html

# Verbose output
pytest tests/ -v
```

### Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Security tests (requires Docker)
pytest tests/security/

# Single test file
pytest tests/unit/test_task_queue.py

# Specific test function
pytest tests/unit/test_task_queue.py::test_enqueue_task
```

### Test Markers

```bash
# Run only fast tests
pytest -m "not slow"

# Run only tests requiring Docker
pytest -m "requires_docker"

# Skip integration tests
pytest -m "not integration"
```

## Test Categories

### Unit Tests (`tests/unit/`)

Fast, isolated tests for individual components:
- No external dependencies
- Mock all I/O operations
- Test business logic and algorithms
- Should run in < 1 second each

Example:
```python
def test_calculate_retry_delay():
    delay = calculate_retry_delay(retry_count=2)
    assert delay == 20  # 5 * 2^2
```

### Integration Tests (`tests/integration/`)

Test interaction between services:
- May use Docker containers
- Test API contracts
- Verify service communication
- May take several seconds

Example:
```python
@pytest.mark.integration
async def test_evaluation_flow():
    # Submit to API
    response = await client.post("/api/eval", json={...})
    
    # Verify in storage
    evaluation = storage.get_evaluation(response["eval_id"])
    assert evaluation.status == "queued"
```

### End-to-End Tests (`tests/e2e/`)

Complete workflow tests:
- Full platform startup
- Real code execution
- Multiple service interaction
- May take minutes

Example:
```python
@pytest.mark.e2e
@pytest.mark.slow
def test_full_evaluation():
    # Submit code
    # Wait for execution
    # Verify output
    # Check all services
```

### Security Tests (`tests/security/`)

Security-focused scenarios:
- Container escape attempts
- Resource exhaustion
- Code injection
- Network isolation

**Note**: These tests run potentially dangerous code in containers. Only run in isolated environments.

### Load Tests (`tests/load/`)

Performance and scalability tests:
- Concurrent evaluations
- Queue throughput
- Memory usage
- Response times

## Writing Tests

### Test Structure

```python
# tests/unit/test_component.py
import pytest
from unittest.mock import Mock, patch

class TestComponent:
    """Tests for Component functionality."""
    
    @pytest.fixture
    def component(self):
        """Create component instance for testing."""
        return Component()
    
    def test_basic_functionality(self, component):
        """Test basic component behavior."""
        # Arrange
        input_data = {"key": "value"}
        
        # Act
        result = component.process(input_data)
        
        # Assert
        assert result.success is True
        assert result.data == expected_data
    
    @patch('external.service')
    def test_with_mock(self, mock_service, component):
        """Test with mocked external dependency."""
        mock_service.return_value = {"mocked": "response"}
        
        result = component.call_service()
        
        mock_service.assert_called_once()
        assert result == {"mocked": "response"}
```

### Fixtures

Common fixtures in `conftest.py`:

```python
@pytest.fixture
def api_client():
    """Test client for API requests."""
    return TestClient(app)

@pytest.fixture
def redis_client():
    """Redis client for tests."""
    return fakeredis.FakeRedis()

@pytest.fixture
def temp_storage():
    """Temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
```

### Markers

Available markers:

```python
@pytest.mark.slow  # Tests taking > 5 seconds
@pytest.mark.integration  # Requires multiple services
@pytest.mark.requires_docker  # Needs Docker daemon
@pytest.mark.security  # Security-related tests
@pytest.mark.flaky  # Known to be unstable
```

## Test Data

### Code Samples (`fixtures/code_samples/`)

Pre-validated code for testing:
- `hello_world.py` - Basic print test
- `infinite_loop.py` - Timeout testing
- `memory_bomb.py` - Resource limit testing
- `network_attempt.py` - Network isolation testing

### Mock Responses (`fixtures/mock_responses/`)

Saved API responses for mocking:
- `executor_success.json`
- `executor_timeout.json`
- `storage_evaluation.json`

## Coverage Requirements

Target coverage by component:
- Core business logic: 90%+
- API endpoints: 85%+
- Error handling: 95%+
- Security features: 100%

Check coverage:
```bash
# Generate HTML report
pytest --cov=. --cov-report=html
open htmlcov/index.html

# Terminal report
pytest --cov=. --cov-report=term-missing
```

## CI/CD Integration

Tests run automatically on:
- Pull requests (unit + integration)
- Main branch commits (all tests)
- Nightly (includes load tests)

GitHub Actions workflow:
```yaml
- name: Run tests
  run: |
    pytest tests/unit/ -v
    pytest tests/integration/ -v --maxfail=3
```

## Debugging Tests

### Verbose Output
```bash
pytest -vv tests/failing_test.py
```

### Drop into debugger
```python
import pdb; pdb.set_trace()
# or
import pytest; pytest.set_trace()
```

### Print during tests
```bash
pytest -s  # Don't capture stdout
```

### Run specific test
```bash
pytest tests/unit/test_queue.py -k "test_enqueue"
```

## Best Practices

1. **Test Independence**: Each test should be runnable in isolation
2. **Clear Names**: Test names should describe what they test
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Mock External Dependencies**: Unit tests shouldn't hit real services
5. **Use Fixtures**: Share common setup via fixtures
6. **Test Edge Cases**: Empty inputs, None values, exceptions
7. **Document Complex Tests**: Add docstrings explaining the scenario

## Common Issues

### Docker Not Available
```
Error: Docker daemon not responding
Solution: Start Docker or skip with: pytest -m "not requires_docker"
```

### Slow Tests
```
Solution: Run fast tests only: pytest -m "not slow"
```

### Flaky Tests
```
Solution: Re-run flaky tests: pytest --reruns 3
```

### Import Errors
```
Solution: Run from project root or set PYTHONPATH
```

## Contributing

1. Write tests for new features
2. Ensure tests pass locally before pushing
3. Add appropriate markers
4. Update test documentation
5. Aim for high coverage without sacrificing quality

## Future Improvements

1. **Contract Testing**: Verify API contracts between services
2. **Mutation Testing**: Test the tests themselves
3. **Visual Regression**: For frontend components
4. **Chaos Testing**: Random failure injection
5. **Performance Regression**: Track performance over time