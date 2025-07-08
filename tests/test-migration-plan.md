# Test Migration Plan

## Overview
This document tracks the migration of valuable test cases from legacy test structures to the current test framework.

## Migration Status

### ✅ Completed Migrations

#### 1. Core Integration Tests
**Migrated from**: Custom test framework (TestResult class pattern)
**Migrated to**: `tests/integration/test_core_flows.py`
**Migration date**: Week 4
**Changes made**:
- Converted from custom TestResult class to pytest assertions
- Added proper pytest markers (@pytest.mark.integration, @pytest.mark.api)
- Integrated with standard test fixtures (api_session)
- Added TODOs for known limitations (timeout enforcement, language support)

#### 2. Security Tests
**Original**: `tests/security_scanner.py` (adapted for current architecture)
**Current**: `tests/security/test_input_validation.py`
**Status**: Adapted and enhanced
**Coverage**:
- Input validation tests
- Payload size limits
- Invalid language handling
- Timeout boundary testing
- Null byte injection protection
- Unicode handling

#### 3. Load and Performance Tests
**Migrated to**: Multiple specialized test files
- `tests/integration/test_load.py` - Concurrent evaluation testing
- `tests/integration/test_resilience.py` - Service failure recovery
- `tests/benchmarks/test_evaluation_throughput.py` - Throughput benchmarking

#### 4. Priority Queue Tests
**Migrated from**: `scripts/test_priority_queue.py` and `scripts/test_priority_celery.py`
**Migrated to**: 
- `tests/integration/test_priority_queue.py` - API-level priority testing
- `tests/integration/test_priority_celery.py` - Direct Celery priority testing
**Migration date**: Week 4
**Changes made**:
- Added proper pytest fixtures and markers
- Integrated with test infrastructure
- Enhanced test coverage

### ✅ Completed Migrations (continued)

#### 5. Docker Event Tests
**Status**: Completed
**Location**: 
- `tests/integration/test_docker_event_diagnostics.py` - Diagnostic timing tests
- `tests/integration/test_fast_failing_containers.py` - Functional verification
**Purpose**: Verify Docker event race condition fixes
**Integration**: Both tests are included in `run_tests.py`

### 📋 Identified for Future Migration

#### 6. End-to-End UI Tests
**Current state**: No automated UI tests
**Proposed location**: `tests/e2e/test_ui_flows.py`
**Priority**: Low (manual testing sufficient for demo)
**Would test**:
- Code submission through UI
- Real-time status updates
- Error display
- Code editor functionality

#### 7. Kubernetes Integration Tests
**Current state**: Not applicable (using Docker Compose)
**Future location**: `tests/integration/test_k8s_deployment.py`
**Timeline**: Post-Kubernetes migration
**Would test**:
- Pod scaling
- Service discovery
- Persistent volume claims
- Network policies

## Migration Principles

1. **Preserve test intent**: Maintain the original test's purpose while modernizing implementation
2. **Add proper markers**: Ensure all tests have appropriate pytest markers for filtering
3. **Use standard fixtures**: Leverage existing test infrastructure (api_session, redis_client, etc.)
4. **Document limitations**: Add TODOs for known issues or platform limitations
4. **Enhance coverage**: Add additional test cases where gaps are identified

## Test Organization Standards

### Markers
All migrated tests should include appropriate markers:
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.api` - Tests requiring API service
- `@pytest.mark.slow` - Tests taking > 5 seconds
- `@pytest.mark.docker` - Tests requiring Docker
- See `pyproject.toml` for complete marker list

### File Structure
```
tests/
├── unit/           # Isolated component tests
├── integration/    # Multi-service tests
├── e2e/           # Full workflow tests
├── security/      # Security-focused tests
├── performance/   # Load and benchmark tests
└── benchmarks/    # Long-running performance measurements
```

## Deferred Test Migrations

Some test categories are intentionally deferred:

1. **Authentication/Authorization Tests**: Deferred until auth system is implemented
2. **Multi-tenant Tests**: Deferred until Kubernetes namespace isolation
3. **GPU Tests**: Deferred until GPU executor support is added
4. **Language-specific Tests**: Currently Python-only (see TODO: LANGUAGE-SUPPORT)

## Validation Checklist

For each migrated test:
- [ ] Original test functionality preserved
- [ ] Proper pytest markers added
- [ ] Integrated with test fixtures
- [ ] Documentation updated
- [ ] Test passes in CI/CD
- [ ] Coverage metrics maintained or improved

## Next Steps

1. ✅ All critical test migrations are complete for Week 4 demo
2. ✅ Test infrastructure is modernized with pytest
3. ✅ Comprehensive marker system implemented
4. ✅ Marker audit script created for ongoing maintenance

The test migration is effectively complete for the current platform state. Future migrations will align with new feature development (Kubernetes, additional languages, authentication).