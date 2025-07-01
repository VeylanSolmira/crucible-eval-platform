# Platform Performance Metrics

## Overview
This document outlines the performance testing framework for the Crucible platform and provides placeholders for actual metrics to be collected during testing.

## Test Environment
- **Hardware**: Local Docker Desktop (adjust for your environment)
- **Services**: All microservices running via docker-compose
- **Date**: Week 4, Day 2 - Test Framework Created

## Load Testing Results

### Concurrent Evaluation Performance

*Note: The test framework is ready. Run `python tests/integration/test_load.py progressive` to collect actual metrics.*

| Concurrent Users | Total Evaluations | Success Rate | Avg Response Time | Throughput |
|-----------------|-------------------|--------------|-------------------|------------|
| 5               | 10                | TBD          | TBD               | TBD        |
| 10              | 20                | TBD          | TBD               | TBD        |
| 20              | 40                | TBD          | TBD               | TBD        |
| 50              | 100               | TBD          | TBD               | TBD        |

### Key Metrics (To Be Measured)

**Submission Latency** (time to accept evaluation):
- Minimum: TBD
- Average: TBD
- Maximum: TBD
- 95th percentile: TBD

**End-to-End Completion Time** (submission to result):
- Simple print statement: Expected 2-3s
- With 1s sleep: Expected 3-4s
- Complex computation: Expected 4-6s
- Timeout handling: Should enforce at 30s

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

### Container Resource Consumption (Estimated)

*Note: Use `docker stats` during load testing to collect actual metrics.*

| Service | CPU (expected) | Memory (expected) | Memory (limit) |
|---------|----------------|-------------------|----------------|
| API | 10-20% | 100-200MB | 512MB |
| Celery Worker | 15-25% | 200-300MB | 512MB |
| Queue Worker | 5-15% | 100-200MB | 512MB |
| Executor | 20-50%* | 200-400MB | 512MB |
| Storage | 5-10% | 50-100MB | 256MB |
| Redis | 5-10% | 32-64MB | 256MB |
| PostgreSQL | 10-20% | 200-300MB | 1GB |

*During active evaluation execution

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
| Infinite loop | At timeout (30s) | Immediate | None |
| Memory exhaustion | Within 5s | Immediate | None |
| Network timeout | At timeout | Automatic retry | None |
| Container crash | Within 5s | 5-10s restart | None |

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

# Progressive load test
python tests/integration/test_load.py progressive
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