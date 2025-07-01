# Testing Master Plan - Crucible Platform

## Overview

This document provides a comprehensive testing strategy for the Crucible platform, covering all components, integration points, and critical system behaviors including security, performance, and correctness.

## Testing Categories

### 1. Component Testing

#### API Service
- **Unit Tests**
  - [ ] Endpoint validation (request/response schemas)
  - [ ] Authentication/authorization logic
  - [ ] Rate limiting functionality
  - [ ] Error handling and status codes
  - [ ] Celery dual-write logic

#### Queue Service
- **Unit Tests**
  - [ ] Task enqueue/dequeue operations
  - [ ] Priority queue ordering
  - [ ] Dead letter queue handling
  - [ ] Queue persistence and recovery
  - [ ] Worker registration/heartbeat

#### Storage Service
- **Unit Tests**
  - [ ] CRUD operations for evaluations
  - [ ] Query filtering and pagination
  - [ ] Data validation
  - [ ] Concurrent access handling
  - [ ] Cleanup/maintenance operations

#### Executor Service
- **Unit Tests**
  - [ ] Container lifecycle management
  - [ ] Resource limit enforcement
  - [ ] Output streaming
  - [ ] Timeout handling
  - [ ] Security isolation

#### Celery Worker
- **Unit Tests**
  - [ ] Task execution flow
  - [ ] Retry logic with exponential backoff
  - [ ] Error handling and recovery
  - [ ] Fixed executor routing (executor-3 only)
  - [ ] Status updates to storage

### 2. Integration Testing

#### Queue System Comparison
- **Current Status**: ⚠️ Partially Implemented
- **Gap Identified**: Only tests completion status, not output correctness
- **Required Tests**:
  - [ ] Submit identical code to both legacy queue and Celery
  - [ ] Compare execution outputs byte-for-byte
  - [ ] Verify exit codes match
  - [ ] Ensure error messages are consistent
  - [ ] Test with various code patterns:
    - Simple print statements
    - Multi-line outputs
    - Error cases (syntax errors, runtime errors)
    - Resource-intensive operations
    - Long-running tasks

**Implementation Plan**:
```python
def test_output_consistency():
    test_cases = [
        # Simple output
        ('print("Hello, World!")', "Hello, World!\n", 0),
        # Multi-line
        ('for i in range(3):\n    print(i)', "0\n1\n2\n", 0),
        # Error case
        ('1/0', "", 1),  # Should have consistent error
        # Import test
        ('import math\nprint(math.pi)', "3.141592653589793\n", 0),
    ]
    
    for code, expected_output, expected_exit_code in test_cases:
        legacy_result = submit_to_legacy_queue(code)
        celery_result = submit_to_celery(code)
        
        assert legacy_result.output == celery_result.output
        assert legacy_result.exit_code == celery_result.exit_code
        assert legacy_result.error == celery_result.error
```

#### Service Communication
- [ ] API → Queue Service submission flow
- [ ] Queue → Executor task dispatch
- [ ] Executor → Storage result persistence
- [ ] Event propagation via Redis
- [ ] Service discovery and health checks

#### End-to-End Flows
- [ ] Code submission → execution → result retrieval
- [ ] Batch submission handling
- [ ] Task cancellation across services
- [ ] Service failure and recovery scenarios

### 3. Security Testing

#### Container Isolation
- [ ] Network isolation verification
  - No outbound internet access
  - No access to host network
  - No inter-container communication
- [ ] Filesystem restrictions
  - Read-only root filesystem
  - No access to host filesystem
  - Temporary directories properly isolated
- [ ] Resource limits enforcement
  - Memory limits respected
  - CPU limits enforced
  - Disk space quotas
  - Process count limits

#### Code Execution Security
- [ ] Privilege escalation attempts blocked
- [ ] Kernel exploit mitigation
- [ ] Fork bomb protection
- [ ] Excessive resource consumption handling
- [ ] Malicious code patterns detected

#### API Security
- [ ] Input validation and sanitization
- [ ] SQL injection prevention
- [ ] Rate limiting effectiveness
- [ ] Authentication bypass attempts
- [ ] Authorization boundary testing

#### Secrets Management
- [ ] No secrets in container images
- [ ] Environment variable isolation
- [ ] No secrets in logs
- [ ] Secure inter-service communication

### 4. Performance Testing

#### Load Testing
- [ ] Concurrent evaluation handling (target: 100 simultaneous)
- [ ] Queue throughput (target: 1000 tasks/minute)
- [ ] API response times under load
- [ ] Storage query performance with large datasets
- [ ] Memory usage under sustained load

#### Stress Testing
- [ ] System behavior at resource limits
- [ ] Graceful degradation patterns
- [ ] Recovery from overload conditions
- [ ] Queue backpressure handling

#### Benchmark Comparisons
- [ ] Legacy queue vs Celery performance
- [ ] Executor scaling characteristics
- [ ] Storage backend options (PostgreSQL vs MongoDB)
- [ ] Redis memory usage patterns

### 5. Reliability Testing

#### Failure Scenarios
- [ ] Service crashes and restarts
- [ ] Network partitions
- [ ] Storage failures
- [ ] Redis connection loss
- [ ] Docker daemon issues

#### Data Integrity
- [ ] No evaluation loss during failures
- [ ] Consistent state after recovery
- [ ] Idempotent operations
- [ ] Transaction guarantees

#### Monitoring and Observability
- [ ] Metrics accuracy
- [ ] Log completeness
- [ ] Trace continuity
- [ ] Alert reliability

## Test Environments

### Local Development
- Docker Compose setup
- Mocked external dependencies
- Fast feedback cycle
- Debugger access

### CI/CD Pipeline
- GitHub Actions workflows
- Automated on PR/push
- Parallel test execution
- Coverage reporting

### Staging Environment
- Production-like configuration
- Real external services
- Performance baselines
- Security scanning

## Test Data Management

### Fixtures
- Standard test code snippets
- Known-good evaluation results
- Error case examples
- Performance test datasets

### Data Generation
- Random code generation
- Load test scenarios
- Fuzzing inputs
- Edge case creation

## Testing Tools and Frameworks

### Current Stack
- **pytest**: Unit and integration tests
- **httpx**: API testing
- **docker-py**: Container testing
- **locust**: Load testing
- **bandit**: Security scanning

### Planned Additions
- **Testcontainers**: Integration test isolation
- **Hypothesis**: Property-based testing
- **OWASP ZAP**: Security testing
- **Chaos Monkey**: Reliability testing

## Test Automation

### Pre-commit Hooks
- Linting (ruff, mypy)
- Unit test subset
- Security checks

### CI Pipeline Stages
1. **Quick Tests** (< 2 min)
   - Linting
   - Type checking  
   - Unit tests

2. **Integration Tests** (< 10 min)
   - Service communication
   - End-to-end flows
   - Container tests

3. **Extended Tests** (< 30 min)
   - Performance benchmarks
   - Security scans
   - Reliability scenarios

### Nightly Runs
- Full regression suite
- Long-running stress tests
- Security audit
- Performance trending

## Test Metrics and Reporting

### Coverage Targets
- Unit tests: 80% line coverage
- Integration tests: All critical paths
- Security tests: OWASP Top 10

### Quality Gates
- All tests passing
- No security vulnerabilities
- Performance within SLAs
- No regression from baseline

### Reporting
- Test results dashboard
- Coverage trends
- Performance graphs
- Security scan results

## Known Gaps and TODOs

### Immediate Priorities
1. **Fix Queue Comparison Test** - Add output validation
2. **Implement Security Test Suite** - Container isolation verification
3. **Add Performance Baselines** - Establish targets
4. **Create Reliability Tests** - Failure injection

### Medium Term
1. Property-based testing for API
2. Fuzzing for code execution
3. Chaos engineering practices
4. Contract testing between services

### Long Term
1. ML-based test generation
2. Automated performance regression detection
3. Security vulnerability prediction
4. Test impact analysis

## Testing Philosophy

1. **Test at Multiple Levels** - Unit, integration, system
2. **Automate Everything** - No manual test steps
3. **Test Early and Often** - Shift left approach
4. **Production-Like Testing** - Real conditions
5. **Security First** - Every feature considers security
6. **Performance Awareness** - Measure everything
7. **Failure is Expected** - Test error paths thoroughly

## References

- [Testing Microservices](https://martinfowler.com/articles/microservice-testing/)
- [Container Security Best Practices](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [Chaos Engineering Principles](https://principlesofchaos.org/)
- [Property-Based Testing](https://hypothesis.works/)