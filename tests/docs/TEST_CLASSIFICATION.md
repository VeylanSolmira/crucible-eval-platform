# Test Classification for Kubernetes Migration

This document classifies all tests as white box, black box, or gray box to help identify which tests need modification for the Kubernetes migration.

## Classification Criteria

### Black Box Tests 🟢
- Only use public APIs (REST endpoints)
- Test external behavior
- Should work regardless of Docker/Kubernetes implementation
- **Migration Impact: Should continue working**

### White Box Tests 🔴
- Access internal implementation details
- Direct service communication (not through APIs)
- Docker-specific features (containers, events, mounts)
- Direct database/Redis access
- File system dependencies
- **Migration Impact: Will likely need modification**

### Gray Box Tests 🟡
- Mostly behavioral but with some implementation knowledge
- May use internal APIs but test behavior
- **Migration Impact: May need minor adjustments**

## Test Classification

### Unit Tests

#### `tests/unit/api/test_evaluation_request.py`
- **Classification: 🟡 GRAY BOX**
- **Reason**: Tests API contract but has hardcoded "docker" as default engine
- **Migration Action**: Update default engine to "kubernetes" or make it configurable

#### `tests/unit/celery/test_retry_config.py`
- **Classification: 🔴 WHITE BOX**
- **Reason**: Tests Celery internals and retry configuration
- **Migration Action**: Verify Celery configuration works in K8s environment

#### `tests/unit/storage/test_database_backend.py`
- **Classification: 🔴 WHITE BOX**
- **Reason**: Direct database access and SQLAlchemy internals
- **Migration Action**: Update connection strings and ensure K8s service discovery works

#### `tests/unit/storage/test_file_backend.py`
- **Classification: 🔴 WHITE BOX**
- **Reason**: File system operations, path dependencies
- **Migration Action**: Update for K8s persistent volumes and mount paths

#### `tests/unit/storage/test_flexible_manager.py`
- **Classification: 🔴 WHITE BOX**
- **Reason**: Tests storage manager internals
- **Migration Action**: Verify storage abstraction works with K8s volumes

#### `tests/unit/storage/test_memory_backend.py`
- **Classification: 🟢 BLACK BOX**
- **Reason**: In-memory operations, no external dependencies
- **Migration Action**: None needed

#### `tests/unit/storage/test_postgresql_operations.py`
- **Classification: 🔴 WHITE BOX**
- **Reason**: Direct PostgreSQL operations
- **Migration Action**: Update for K8s StatefulSet PostgreSQL

### Integration Tests

#### `tests/integration/test_core_flows.py`
- **Classification: 🟢 BLACK BOX**
- **Reason**: Tests end-to-end flows through public APIs
- **Migration Action**: Should work as-is

#### `tests/integration/test_evaluation_lifecycle.py`
- **Classification: 🟢 BLACK BOX**
- **Reason**: Tests evaluation lifecycle through APIs
- **Migration Action**: Should work as-is

#### `tests/integration/test_celery_*.py` (all Celery tests)
- **Classification: 🔴 WHITE BOX**
- **Reason**: Direct Celery/Redis communication
- **Migration Action**: Update for K8s service names and networking

#### `tests/integration/test_docker_event_diagnostics.py`
- **Classification: 🔴 WHITE BOX**
- **Reason**: Docker-specific event handling
- **Migration Action**: Replace with K8s event monitoring or remove

#### `tests/integration/test_executor_imports.py` (DEPRECATED)
- **Classification: 🔴 WHITE BOX**
- **Reason**: Tests executor service internals
- **Status**: DEPRECATED - Replaced by test_evaluation_job_imports.py

#### `tests/integration/test_evaluation_job_imports.py`
- **Classification: 🟢 BLACK BOX**
- **Reason**: Tests comprehensive import scenarios via API endpoints
- **Migration Action**: None needed - designed for K8s architecture
- **Note**: Consolidated test file that covers all import handling scenarios for Kubernetes Jobs

#### `tests/integration/test_fast_failing_containers.py`
- **Classification: 🔴 WHITE BOX**
- **Reason**: Docker container lifecycle testing
- **Migration Action**: Rewrite for K8s pod lifecycle

#### `tests/integration/test_redis_cleanup.py`
- **Classification: 🔴 WHITE BOX**
- **Reason**: Direct Redis access
- **Migration Action**: Update Redis connection for K8s service

#### `tests/integration/test_network_isolation.py`
- **Classification: 🟡 GRAY BOX**
- **Reason**: Tests network behavior but may have Docker assumptions
- **Migration Action**: Verify K8s network policies provide same isolation

#### `tests/integration/test_filesystem_isolation.py`
- **Classification: 🟡 GRAY BOX**
- **Reason**: Tests isolation behavior
- **Migration Action**: Verify K8s security contexts provide same isolation

### Security Tests

#### `tests/security/test_input_validation.py`
- **Classification: 🟢 BLACK BOX**
- **Reason**: Tests API input validation
- **Migration Action**: Should work as-is

### Manual Tests

#### `tests/manual/test_db_flow.py`
- **Classification: 🔴 WHITE BOX**
- **Reason**: Direct database operations
- **Migration Action**: Update for K8s database access

#### `tests/manual/test_storage_direct.py`
- **Classification: 🔴 WHITE BOX**
- **Reason**: Direct storage access
- **Migration Action**: Update for K8s storage model

## Summary

### Test Migration Priority

1. **Keep Working** (Black Box - 6 tests):
   - Core flows
   - Evaluation lifecycle
   - Input validation
   - Memory backend
   - API request validation (minor update)

2. **Need Updates** (White Box - 16 tests):
   - All Celery tests
   - Docker-specific tests
   - Direct storage tests
   - Database tests
   - Redis tests

3. **Minor Updates** (Gray Box - 3 tests):
   - Network isolation
   - Filesystem isolation
   - API defaults

### Recommended Actions

1. **Immediate**: Run black box tests to ensure basic functionality
2. **Short Term**: Update gray box tests for K8s defaults
3. **Medium Term**: Rewrite white box tests for K8s architecture
4. **Long Term**: Create new K8s-specific integration tests

### Running Tests by Category

```bash
# Run only black box tests (should work immediately)
pytest -m blackbox

# Run gray box tests (may need minor fixes)
pytest -m graybox

# Run white box tests (expect failures)
pytest -m whitebox

# Run non-white box tests (more likely to pass)
pytest -m "not whitebox"
```

## Notes

- Consider creating a separate test suite for K8s-specific features
- Some white box tests might be converted to black box by using APIs instead of internals
- Docker-specific tests should be replaced with K8s equivalents, not just removed