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
│   ├── test_queue_executor_integration.py
│   ├── test_core_flows.py      # Complete evaluation flow tests
│   ├── test_load.py           # Load and concurrent testing
│   └── test_resilience.py     # Service failure recovery
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
├── run_demo_tests.py      # Automated demo test runner
├── fixtures/              # Test data and fixtures
│   ├── code_samples/
│   └── mock_responses/
└── conftest.py           # Pytest configuration and shared fixtures
```

## Running Tests

### Kubernetes Test Orchestrator

The test orchestrator automatically detects your cluster type and configures itself accordingly:

**Automatic Cluster Detection:**
- **Local clusters** (kind, minikube, docker-desktop): Builds images locally, loads into cluster
- **Remote clusters** (EKS, GKE, AKS): Builds images, pushes to registry (ECR/Docker Hub)

```bash
# Run all tests in cluster
python tests/test_orchestrator.py

# Run specific test suites
python tests/test_orchestrator.py unit integration

# Run specific test files (use relative path from tests/ directory)
python tests/test_orchestrator.py --test-files integration/test_celery_connection.py

# Run multiple specific test files
python tests/test_orchestrator.py --test-files integration/test_celery_connection.py integration/test_celery_tasks.py

# Skip building test image (uses latest)
python tests/test_orchestrator.py integration --skip-build

# Run tests in parallel
python tests/test_orchestrator.py --parallel

# Include slow tests
python tests/test_orchestrator.py --include-slow

# Include destructive tests
python tests/test_orchestrator.py --include-destructive
```

The test orchestrator:
1. Runs smoke tests to verify cluster readiness
2. Builds and pushes a test runner Docker image
3. Creates a coordinator job in Kubernetes
4. Runs tests inside the cluster with proper service access
5. Streams logs and aggregates results

This is especially useful for integration tests that need to access cluster services like Redis, PostgreSQL, etc.

### Configuration

The test orchestrator can be configured via environment variables:

```bash
# Force production mode (always push to registry)
PRODUCTION_MODE=true python tests/test_orchestrator.py

# Use specific namespace
K8S_NAMESPACE=staging python tests/test_orchestrator.py

# Override image pull policy (default: auto-detected)
IMAGE_PULL_POLICY=Always python tests/test_orchestrator.py

# Use specific registry
ECR_REGISTRY=123456.dkr.ecr.us-west-2.amazonaws.com python tests/test_orchestrator.py
```

**Environment Variables:**
- `K8S_NAMESPACE`: Target namespace (default: crucible)
- `PRODUCTION_MODE`: Force registry usage (default: auto-detected)
- `IMAGE_PULL_POLICY`: Override pull policy (default: Never for local, IfNotPresent for remote)
- `ECR_REGISTRY`: ECR registry URL (required for remote clusters)
- `DOCKER_HUB_USER`: Docker Hub username (alternative to ECR)

### Local Testing

For running tests locally (requires port forwarding):

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

# Run only load tests
pytest -m "load"

# Run integration tests but skip load tests
pytest -m "integration and not load"

# Run fast load tests only (skip slow ones)
pytest -m "load and not slow"
```

### Demo Test Runner

Run the automated demo test suite:

```bash
# Full demo test suite
python tests/run_demo_tests.py

# Quick platform check
python tests/run_demo_tests.py quick
```

### New Integration Tests

#### Core Flow Tests (`integration/test_core_flows.py`)
```bash
python tests/integration/test_core_flows.py
```
Tests:
- Health check verification
- Simple evaluation submission
- Full evaluation lifecycle tracking
- Error handling scenarios
- Concurrent evaluation handling
- Storage retrieval verification

#### Load Testing (`integration/test_load.py`)
```bash
# Default: 20 concurrent, 100 total
python tests/integration/test_load.py

# Custom: 10 concurrent, 20 total with timeout
python tests/integration/test_load.py 10 20

# With custom timeout (10 minutes)
python tests/integration/test_load.py 10 20 600

# Sustained load test
python tests/integration/test_load.py sustained 60

# Using pytest (runs smaller preset tests)
pytest tests/integration/test_load.py -v
```

This test respects nginx rate limits (10 req/s) and includes:
- Redis event monitoring for real-time status updates
- State machine validation to handle out-of-order events
- Final status verification against storage service
- Detailed performance metrics in JSON output
- Rate limiting with token bucket algorithm

#### Resilience Testing (`integration/test_resilience.py`)
```bash
python tests/integration/test_resilience.py
```
Tests:
- Service restart during evaluation
- Celery worker failure recovery
- Storage service outage handling
- Network partition simulation

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
@pytest.mark.load  # Load/performance tests (excluded by default)
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