# Week 7: Test Infrastructure & Client Migration
**Dates**: July 20-26, 2025  
**Focus**: Improve test infrastructure reliability and migrate to Kubernetes Python client
**Goal**: Robust testing framework with secure, type-safe Kubernetes integration

## Completed This Week ✅

### 1. Test Infrastructure Improvements
- [x] Fixed coordinator to support individual test files in subdirectories
  - [x] Now accepts paths like `unit/storage/test_postgresql_operations.py`
  - [x] Fixed job name length limitations
- [x] Moved PostgreSQL integration tests from unit to integration suite
  - [x] Added proper database setup for integration tests
  - [x] All unit tests now passing (134 tests, 0 failures)
- [x] Fixed race condition in test orchestrator
  - [x] Added `kubectl wait` to ensure job completion before status check
  - [x] Eliminated misleading "Tests failed" messages

### 2. Test Environment Configuration
- [x] Added TEST_DATABASE_URL to test job environment variables
- [x] Configured test jobs to connect to cluster PostgreSQL
- [x] Proper separation of unit vs integration test requirements

## Next Sprint Tasks 🚀

### 1. Kubernetes Python Client Migration

#### 1.1 Foundation Setup
- [ ] Add kubernetes package to requirements
- [ ] Create client initialization module
  - [ ] Support both in-cluster and kubeconfig authentication
  - [ ] Implement proper connection pooling
  - [ ] Add retry logic with exponential backoff
- [ ] Document migration approach
  - [ ] See [Kubernetes Client Migration Plan](../../architecture/kubernetes-client-migration.md)

#### 1.2 Core Function Migration
- [ ] Replace kubectl subprocess calls in test_orchestrator.py
  - [ ] Job creation (`kubectl apply` → `create_namespaced_job`)
  - [ ] Job status checking (`kubectl get` → `read_namespaced_job`)
  - [ ] Job waiting (`kubectl wait` → Watch API)
  - [ ] Log streaming (`kubectl logs` → `read_namespaced_pod_log`)
- [ ] Migrate coordinator.py kubectl usage
  - [ ] Test job creation
  - [ ] Pod monitoring
  - [ ] Log collection

#### 1.3 Enhanced Features
- [ ] Implement real-time job monitoring
  - [ ] Use Watch API for event-based updates
  - [ ] Stream logs as jobs run
  - [ ] Better progress reporting
- [ ] Add structured error handling
  - [ ] Specific exceptions for different failure modes
  - [ ] Better error messages for common issues
  - [ ] Automatic retry for transient failures

### 2. Test Framework Enhancements

#### 2.1 Test Result Reporting
- [ ] Enhance custom pytest hook
  - [ ] Include test durations
  - [ ] Add failure details
  - [ ] Support for xfail and skip reasons
- [ ] Create unified test dashboard
  - [ ] Real-time test progress
  - [ ] Historical test results
  - [ ] Failure trends

#### 2.2 Test Environment Management
- [ ] Automated test database setup
  - [ ] Create test_crucible database if missing
  - [ ] Database migration support
  - [ ] Test data fixtures
- [ ] Environment validation
  - [ ] Pre-flight checks for required services
  - [ ] Clear error messages for missing dependencies
  - [ ] Automatic fallback for local development

#### 2.3 Docker to Kubernetes Test Migration
- [ ] Migrate Docker event diagnostic tests
  - [ ] Transform container lifecycle tests to Job lifecycle monitoring
  - [ ] Replace Docker event tests with Kubernetes status latency tests
  - [ ] Update log capture tests for Kubernetes pod logs
  - [ ] See [Kubernetes Job Monitoring Tests Migration](../../testing/kubernetes-job-monitoring-tests.md)
- [ ] Focus on Kubernetes-native testing
  - [ ] Measure Job state transition latencies
  - [ ] Test concurrent Job handling capabilities
  - [ ] Prepare for event-driven architecture testing
  - [ ] Create performance baselines for optimization

#### 2.4 Test Code Quality Audit
- [ ] Audit all tests for diagnostic print anti-pattern
  - [ ] Identify tests with print statements after assertions (unreachable on failure)
  - [ ] Example: test_available_libraries.py has prints after assertions - never seen when needed
  - [ ] Replace with better assertion messages: `assert condition, f"Diagnostic info: {value}"`
  - [ ] Move critical diagnostic output before assertions or use proper logging
  - [ ] Consider pytest fixtures for diagnostic output that runs regardless of test outcome

#### 2.5 Test Environment Architecture Review
- [ ] Review and optimize test environment strategy
  - [ ] See [Test Environment Architecture](../../testing/test-environment-architecture.md)
  - [ ] Evaluate local vs test overlay usage patterns
  - [ ] Implement namespace-per-PR strategy for CI/CD
  - [ ] Create lightweight test mode to reduce resource usage
  - [ ] Audit and minimize test-runner RBAC permissions
- [ ] CI/CD test environment setup
  - [ ] Configure GitHub Actions to use test overlay
  - [ ] Implement dynamic namespace creation for PR tests
  - [ ] Add automatic cleanup of test namespaces
  - [ ] Create test data seeding mechanism
- [ ] Security hardening
  - [ ] Remove test permissions from production paths
  - [ ] Implement resource quotas for test namespaces
  - [ ] Add network policies for test pod isolation
  - [ ] Regular RBAC permission audits

### 3. System Improvements

#### 3.1 Log Shipping Infrastructure
- [ ] Implement centralized log collection
  - [ ] Deploy Fluent Bit as DaemonSet for log collection
  - [ ] Configure to capture container logs before pod deletion
  - [ ] Ship logs to persistent storage (CloudWatch/Elasticsearch)
  - [ ] Essential due to aggressive cleanup controller deleting pods immediately
  - [ ] Current test log buffering only works during test runs, not production
  - [ ] See [Log Shipping Architecture](../../architecture/log-shipping-architecture.md)

#### 3.2 Cleanup Controller Enhancement
- [ ] Fix cleanup controller deleting Pending pods with failed containers
  - [ ] Remove container status check that deletes Pending pods (lines 55-58)
  - [ ] Only delete pods in terminal states (Failed, Succeeded, Error)
  - [ ] Prevents evaluation pods from being deleted before they can run
  - [ ] Discovered when integration tests showed "Has logs: False" for all evaluations

#### 3.3 Storage Worker Event Field Migration
- [ ] Fix storage-worker missing field errors for Kubernetes events
  - [ ] Update dispatcher to populate executor_id with job name
  - [ ] Update dispatcher to populate container_id with pod name
  - [ ] OR: Update storage-worker to make these fields optional for Kubernetes
  - [ ] Remove error logs for missing non-critical fields
  - [ ] Document the field mapping between Docker and Kubernetes architectures

#### 3.4 Subprocess Elimination
- [ ] Remove all subprocess.run calls
  - [ ] Audit codebase for subprocess usage
  - [ ] Replace with appropriate Python libraries
  - [ ] Document any remaining shell requirements
- [ ] Input validation
  - [ ] Validate all user inputs
  - [ ] Sanitize paths and identifiers
  - [ ] Implement allowlists where appropriate

#### 3.5 RBAC Enhancement
- [ ] Tighten Kubernetes permissions
  - [ ] Minimal permissions for test coordinator
  - [ ] Separate service accounts per component
  - [ ] Network policies for test isolation

#### 3.6 ResourceQuota Handling
- [ ] Implement proper retry behavior for ResourceQuota errors
  - [ ] See [Kubernetes ResourceQuota Handling](../../architecture/kubernetes-resourcequota-handling.md)
  - [ ] Update dispatcher to return 429 for quota exceeded errors
  - [ ] Verify Celery retries tasks when quota is exhausted
  - [ ] Add monitoring for quota pressure and retry rates
  - [ ] Consider long-term job queueing solution

## Technical Debt to Address
- [ ] Remove debug print statements from test_orchestrator.py
- [ ] Consolidate test configuration (move from hardcoded to config file)
- [ ] Add proper logging instead of print statements
- [ ] Create test cleanup automation for failed jobs
- [ ] Implement executor image resolution design
  - [ ] See [Executor Image Resolution Design](../../architecture/executor-image-resolution-design.md)
  - [ ] Phase 1: Update dispatcher to query node images for local dev
  - [ ] Phase 2: Build lightweight executor registry service for production
  - [ ] Remove ConfigMap-based approach entirely
- [ ] Fix cancellation race condition with orphaned Kubernetes jobs
  - [ ] See [Cancellation Race Condition Analysis](../../architecture/cancellation-race-condition.md)
  - [ ] Implement interim orphan job cleanup (scan every 5 minutes)
  - [ ] Add metrics for orphaned jobs found/cleaned
  - [ ] Design permanent solution (token-based or state machine)

## Success Metrics
- Zero false "test failed" messages
- All subprocess calls replaced with Python clients
- Test execution time reduced by 20%
- 100% of security vulnerabilities from subprocess eliminated

## Notes
- The Kubernetes Python client migration is the primary focus
- This will improve security, reliability, and maintainability
- Expected to reduce debugging time significantly
- Will enable more advanced test orchestration features

## Dependencies
- Kubernetes Python client library
- Updated test container images
- Documentation updates for new patterns