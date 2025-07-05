# Benchmarks

This directory contains benchmark tests that establish baseline performance metrics and track improvements over time.

## Purpose

Benchmarks are used to:
- Establish performance baselines for the platform
- Track performance improvements/regressions across releases
- Identify bottlenecks and optimization opportunities
- Provide data for capacity planning

## Characteristics

- **Long-running**: Typically run for 60+ seconds to get stable results
- **Resource-intensive**: May consume significant CPU/memory/network
- **Controlled conditions**: Run in isolation with consistent environment
- **Metric-focused**: Output detailed performance data (not just pass/fail)
- **Comparative**: Results compared against previous runs

## Running Benchmarks

Benchmarks are typically run separately from regular tests:

```bash
# Run all benchmarks
python tests/benchmarks/test_evaluation_throughput.py

# Run with custom parameters
TARGET_RPS=5 TEST_DURATION_SECONDS=120 python tests/benchmarks/test_evaluation_throughput.py
```

## Current Benchmarks

### test_evaluation_throughput.py
Measures the platform's ability to handle sustained evaluation load.

**Key Metrics:**
- Evaluations per minute (throughput)
- Latency percentiles (P50, P95, P99)
- Queue depth over time
- Executor utilization
- Error rates under load

**Success Criteria:**
- ≥ 100 evaluations/minute
- P95 latency ≤ 30 seconds
- No evaluation losses
- ≥ 99% submission success rate

## Benchmark Results

Results are saved as JSON files with timestamps:
- `throughput_test_results.json` - Latest throughput benchmark
- Historical results should be stored in `results/` subdirectory

## When to Run Benchmarks

- Before major releases
- After performance optimizations
- When changing core components (executors, queue, storage)
- For capacity planning decisions

## Benchmark vs Performance Tests

| Aspect | Benchmarks | Performance Tests |
|--------|-----------|------------------|
| Duration | Long (60+ seconds) | Short (5-30 seconds) |
| Purpose | Measure capacity | Verify requirements |
| CI/CD | Optional/nightly | Every commit |
| Output | Detailed metrics | Pass/fail |
| Resource usage | High | Moderate |

## Adding New Benchmarks

When creating new benchmarks:
1. Focus on end-to-end user scenarios
2. Include warmup periods
3. Generate comparative metrics
4. Save results in JSON format
5. Document success criteria
6. Consider resource cleanup

## Future Benchmarks

Planned benchmarks to add:
- Storage write throughput
- API endpoint response times
- Large evaluation handling (10MB+ outputs)
- WebSocket connection scaling
- Database query performance