# Performance Tests

This directory contains performance tests that verify the system meets specific performance requirements.

## Purpose

Performance tests ensure that:
- The system meets defined performance SLAs
- Performance regressions are caught early
- Critical operations complete within acceptable time
- Resource usage stays within limits

## Characteristics

- **Pass/fail criteria**: Clear performance thresholds
- **CI/CD friendly**: Run on every commit/PR
- **Quick execution**: Complete in seconds to minutes
- **Specific scenarios**: Test particular operations
- **Deterministic**: Consistent results across runs

## Running Performance Tests

Performance tests run as part of the standard test suite:

```bash
# Run all tests including performance
python tests/run_tests.py

# Run only performance tests
python tests/run_tests.py performance
```

## Test Categories

### Response Time Tests
Verify operations complete within acceptable time:
- API endpoint response < 100ms
- Evaluation submission < 500ms
- Status retrieval < 50ms

### Concurrency Tests
Ensure system handles parallel operations:
- 10 concurrent evaluations without errors
- Multiple users accessing results
- Parallel API requests

### Resource Tests
Verify resource consumption stays reasonable:
- Memory usage < 1GB for 100 evaluations
- No memory leaks after extended operation
- CPU usage scales linearly with load

### Throughput Tests
Ensure minimum processing rates:
- Process 10 evaluations/minute minimum
- Handle 100 API requests/second
- Complete simple evaluations in < 5 seconds

## Writing Performance Tests

```python
def test_api_response_time():
    """API health check should respond in < 100ms"""
    start = time.time()
    response = requests.get(f"{API_URL}/health")
    duration = time.time() - start
    
    assert response.status_code == 200
    assert duration < 0.1, f"Response took {duration*1000:.0f}ms (limit: 100ms)"
```

## Performance Requirements

Current performance requirements:
- API response time: < 100ms (health), < 500ms (operations)
- Evaluation latency: < 5s (simple), < 30s (complex)
- Concurrent users: 10+
- Queue processing: < 5s delay
- Memory per evaluation: < 50MB

## Performance vs Benchmarks

| Aspect | Performance Tests | Benchmarks |
|--------|------------------|-----------|
| Purpose | Verify requirements | Measure capacity |
| Duration | Seconds | Minutes |
| CI/CD | Every commit | Nightly/manual |
| Result | Pass/fail | Metrics |
| Scope | Specific operations | Full system |

## Monitoring Performance

Performance tests should:
1. Use consistent test data
2. Run in isolated environment
3. Account for warmup time
4. Report clear pass/fail
5. Log metrics for trends

## Common Issues

- **Flaky tests**: Add retries or increase timeouts
- **Environment differences**: Use relative thresholds
- **Cold starts**: Include warmup phase
- **Network variability**: Test locally first