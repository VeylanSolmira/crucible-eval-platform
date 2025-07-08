# Platform Performance Metrics

## Overview
This document outlines the performance testing framework for the Crucible platform and provides placeholders for actual metrics to be collected during testing.

## Test Environment
- **Hardware**: Local Docker Desktop (adjust for your environment)
- **Services**: All microservices running via docker-compose
- **Date**: Week 4, Day 2 - Test Framework Created

## Load Testing Results

### Concurrent Evaluation Performance

*Updated: Week 5, Day 2 - Using rate-aware load testing with state machine validation*

| Concurrent Users | Total Evaluations | Success Rate | Avg Response Time | Throughput |
|-----------------|-------------------|--------------|-------------------|------------|
| 5               | 10                | 100%         | 15.7s             | 0.31/s     |
| 10              | 20                | 100%         | 73.2s             | 0.07/s     |
| 20              | 50                | 100%         | 176.8s            | 0.08/s     |
| 50              | 100               | 98%*         | 185.6s            | 0.16/s     |

*Note: Throughput is constrained by nginx rate limiting (10 req/s) and limited executor pool (3 executors)*

**50/100 Test Note**: The 98% success rate reflects 2 evaluations stuck in "running" status due to a race condition in the executor service. These fast print statements (`eval_20250707_104717_9467a26c` and `eval_20250707_104723_a06b63aa`) completed so quickly that their "completed" events arrived while still in "provisioning" status. **Temporary fix applied**: Added provisioning→completed transition. **Long-term fix planned**: Implement event queue with guaranteed ordering (see [executor-event-ordering.md](/docs/architecture/executor-event-ordering.md)).

**Important Note on Timing Accuracy**: The completion times reported by the load test may be longer than actual completion times. The platform needs full "State Machine Adoption Across Services" (see Week 5 Future Work) to ensure accurate timing. Currently, out-of-order events can cause evaluations to complete earlier than detected by the monitoring system. The test includes a verification step to correct final states, but the reported completion times may still be inflated.

### Key Metrics (Measured)

**Submission Latency** (time to accept evaluation):
- Minimum: 0.024s (20/50 test)
- Average: 0.045s - 0.062s
- Maximum: 0.161s
- Median: 0.024s - 0.063s

**End-to-End Completion Time** (submission to result):
- Average: 73.2s (10/20 test) to 176.8s (20/50 test)
- Maximum: 301.8s (10/20 test) to 604.5s (20/50 test)
- Note: High completion times due to queueing (only 3 executors)
- Actual execution time: 1.0-1.3s average (consistent across tests)

### Queue Performance (Expected Behavior)

**Celery Task Processing**:
- Task acceptance: Expected < 50ms
- Queue latency: Expected < 100ms typical
- Worker startup: Observed ~2-3s
- Retry handling: Exponential backoff configured

**50/50 Traffic Split** (during migration):
- Old queue system: Should handle 50% of traffic
- Celery system: Should handle 50% of traffic
- Goal: No dropped tasks during split operation

## Resilience Testing Framework

### Service Restart Tests (To Be Validated)

*Note: Run `python tests/integration/test_resilience.py` to validate these behaviors.*

**Queue Worker Restart**:
- Expected: Evaluations continue after restart
- Expected: No data loss
- Expected recovery time: 5-10 seconds

**Celery Worker Failure**:
- Expected: Tasks remain queued during outage
- Expected: Automatic processing on recovery
- Expected: No duplicate executions

**Storage Service Outage**:
- Expected: Graceful degradation
- Expected: Data persisted after recovery
- Expected: API handles missing storage gracefully

### Network Partition Handling
- Test available for basic connectivity
- Expected: Services reconnect automatically
- Expected: Redis connection pooling handles transient failures

## Resource Usage

### Container Resource Consumption (Measured During Load Tests)

*Measured using `docker stats` during active evaluation processing*

| Service | CPU (idle) | CPU (load) | Memory (actual) | Memory (limit) |
|---------|------------|------------|-----------------|----------------|
| API | 3-4% | 10-15% | 90-95MB | 128MB |
| Celery Worker | 7-8% | 15-20% | 165-170MB | 256MB |
| Storage Worker | <1% | 2-5% | 47-48MB | 128MB |
| Executor (x3) | 1-3% | 20-40%* | 49-50MB | 128MB |
| Storage Service | <1% | 5-8% | 65-66MB | 256MB |
| Redis (main) | 6-8% | 10-15% | 12-13MB | 100MB |
| Redis (celery) | 6-7% | 8-12% | 13-14MB | 300MB |
| PostgreSQL | 1-2% | 5-10% | 25-26MB | 7.6GB** |
| Nginx | <1% | 1-2% | 10-11MB | 7.6GB** |
| Frontend | <1% | <1% | 56-57MB | 7.6GB** |

*During active evaluation execution
**Default Docker memory limit (no explicit limit set)

### Scaling Observations

**Horizontal Scaling Potential**:
- API: Stateless, easily scalable
- Celery Workers: Scale with `--concurrency` flag
- Executors: Can run multiple instances
- Storage: Requires shared backend for scaling

**Bottlenecks Identified**:
1. Docker socket access (single daemon)
2. PostgreSQL connection pool (configurable)
3. Redis memory (for large result storage)

## Error Handling Performance (Test Scenarios)

### Failure Scenarios to Test

| Scenario | Expected Detection | Expected Recovery | Expected Data Loss |
|----------|-------------------|-------------------|-------------------|
| Invalid code syntax | Immediate | N/A | None |
| Infinite loop | At timeout (30s)* | Immediate | None |
| Memory exhaustion | Within 5s | Immediate | None |
| Network timeout | At timeout | Automatic retry | None |
| Container crash | Within 5s | 5-10s restart | None |

*Note: Timeout enforcement is not yet fully implemented. See Week 5 Future Work - "Evaluation Timeout Enforcement"

### Error Handling Design
- Syntax errors: Should be caught by executor
- Runtime errors: Should be captured in logs
- Resource limits: Enforced by Docker
- Timeouts: Configured at multiple levels

## Recommendations

### For Demo
1. **Optimal Load**: 10-20 concurrent evaluations
2. **Response Time**: Expect 2-4s end-to-end
3. **Reliability**: 100% success rate at moderate load

### For Production
1. **Scale Celery Workers**: Use `--concurrency=4` per worker
2. **Add Redis Sentinel**: For high availability
3. **PostgreSQL Pooling**: Increase max connections
4. **Monitoring**: Add Prometheus metrics
5. **Rate Limiting**: Implement per-user limits

## Test Automation

### Available Test Suites
```bash
# Quick health check
python tests/run_demo_tests.py quick

# Full integration suite
python tests/run_demo_tests.py

# Load test with custom parameters
python tests/integration/test_load.py 20 50

# Sustained load test
python tests/integration/test_load.py sustained 60
```

### Continuous Monitoring
- Flower dashboard: http://localhost:5555
- API health: http://localhost:8000/api/health
- Container stats: `docker stats`

## Test Execution Plan

To populate this document with actual metrics:

1. **Start the platform**: `./start-platform.sh`
2. **Run integration tests**: `python tests/integration/test_core_flows.py`
3. **Run load tests**: `python tests/integration/test_load.py progressive`
4. **Run resilience tests**: `python tests/integration/test_resilience.py`
5. **Monitor resources**: `docker stats` during tests
6. **Update this document** with actual results

## Expected Outcomes

Based on the architecture, we expect:
1. **Reliable** evaluation processing with proper queueing
2. **Resilient** service recovery after failures
3. **Predictable** performance under load
4. **Successful** 50/50 traffic split during migration

The test framework is ready to validate these expectations.

## Remaining Metrics to Collect

To complete this document, the following tests need to be run:

1. **Large Load Test (50/100)**:
   ```bash
   source venv/bin/activate && MONITOR_MODE=redis python tests/integration/test_load.py 50 100 600
   ```

2. **Resilience Tests**:
   ```bash
   pytest -m destructive tests/integration/test_resilience.py -v
   ```
   
3. **Error Handling Tests**:
   - Test invalid syntax handling
   - Test infinite loop timeout behavior
   - Test memory exhaustion limits
   
4. **Resource Monitoring During Load**:
   - Run `docker stats` during a sustained load test
   - Capture peak CPU and memory usage under stress

Note: Some tests (like resilience tests) are destructive and will restart services. Run them when the platform is not being used for other purposes.