# Integration Tests

This directory contains integration tests that verify the interaction between multiple components of the METR evaluation platform. These tests focus on service-to-service communication and component integration, but do NOT test complete user workflows (those are in `/tests/e2e/`).

## What Belongs Here

- **Service connectivity tests** - Can services connect to each other?
- **Component integration** - Do components work together correctly?
- **Database operations** - Can services interact with the database?
- **Message passing** - Are messages properly sent between services?
- **Library availability** - What libraries are available in containers?

## What Does NOT Belong Here

- **Complete evaluation workflows** → Moved to `/tests/e2e/`
- **Full system load testing** → Moved to `/tests/e2e/`
- **End-to-end security validation** → Moved to `/tests/e2e/`
- **User journey tests** → Moved to `/tests/e2e/`

## Test Configuration

All integration tests use the centralized configuration from `k8s_test_config.py` which provides:
- API_URL: The API endpoint (defaults to http://localhost:8080)
- REDIS_URL: Redis connection URL (defaults to redis://localhost:6379)
- Other service endpoints as needed

## Test Files

### Service Connectivity Tests

#### `test_celery_connection.py`
Tests basic Celery connectivity:
- Redis connection to broker
- Celery broker connection validation
- Celery configuration correctness

#### `test_postgresql_operations.py`
Tests database connectivity and operations:
- Connection establishment
- Basic CRUD operations
- Transaction handling

### Component Integration Tests

#### `test_available_libraries.py`
Verifies what Python libraries are available in evaluation containers.

#### `test_evaluation_job_imports.py`
Tests import handling in Kubernetes Jobs:
- Standard library imports
- ML library availability
- Error handling for failed imports

### Utility Scripts

#### `check_redis_state.py`
Utility script to check current Redis state and running evaluations.

### Celery Integration Tests

#### `test_celery_connection.py`
Tests basic Celery connectivity:
- Redis connection
- Celery broker connection
- Celery configuration validation

#### `test_celery_tasks.py`
Tests direct Celery task execution:
- Health check task
- Evaluate code task
- Sequential task execution
- Task state tracking

#### `test_celery_integration.py`
Tests Celery integration with the full system (currently skipped - needs K8s updates).

#### `test_celery_cancellation.py`
Tests task cancellation functionality.

### Container & Job Tests

#### `test_evaluation_job_imports.py`
Comprehensive import handling tests for Kubernetes Jobs:
- Standard library imports
- Import error handling
- ML library availability in executor-ml image
- Python environment validation
- Complex import patterns
- Subprocess functionality

#### `test_fast_failing_containers.py`
Tests handling of containers that exit quickly:
- Log capture from fast-failing pods
- Mixed stdout/stderr handling
- Prevention of stuck evaluations
- Extremely fast exit scenarios

#### `test_docker_event_diagnostics.py`
Diagnostic tests for container lifecycle timing and event handling.

### Security Tests

#### `test_network_isolation.py`
Verifies network isolation for evaluation pods:
- Socket connections blocked
- HTTP requests blocked
- DNS resolution blocked
- Local network access blocked

#### `test_filesystem_isolation.py`
Tests filesystem isolation (requires gVisor for full isolation):
- Read-only root filesystem
- Sensitive file protection
- Adapts to gVisor availability

### Queue & Priority Tests

#### `test_priority_queue.py`
Tests priority queue API endpoints and status reporting.

#### `test_load.py`
Load testing for concurrent evaluations.

### Database Tests

#### `test_postgresql_operations.py`
Tests PostgreSQL database operations and persistence.

### Status & Monitoring Tests

#### `test_evaluation_status_display.py`
Tests evaluation status display functionality.

#### `test_status_update_comprehensive.py`
Comprehensive status update testing.

#### `diagnose_status_update.py`
Diagnostic script for troubleshooting status update issues.

### Other Tests

#### `test_available_libraries.py`
Checks which Python libraries are available in evaluation containers.

#### `test_production_requirements.py`
Validates production environment requirements.

### Utilities

#### `conftest.py`
Pytest configuration and shared fixtures for integration tests.

### Legacy Tests

#### `legacy/test_executor_imports.py`
Deprecated tests from the old Docker-based executor service. Replaced by `test_evaluation_job_imports.py`.

## Running Integration Tests

To run all integration tests:
```bash
pytest tests/integration/ -v
```

To run a specific test file:
```bash
pytest tests/integration/test_redis_cleanup.py -v
```

To run with the test orchestrator (in Kubernetes):
```bash
python tests/test_orchestrator.py tests/integration/test_redis_cleanup.py
```

## Test Status

See `tests/docs/initial-kubernetes-test.md` for detailed test status and known issues.