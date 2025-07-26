# Future Load Tests

When you're ready to create dedicated load tests, they could include:

## 1. Throughput Test

```python
@pytest.mark.load
def test_evaluation_throughput():
    """Measure max evaluations/second the system can sustain"""
    # Submit evaluations at increasing rates
    # Find the breaking point
    # Measure queue depths, latencies
```

## 2. Resource Exhaustion Test

```python
@pytest.mark.load  
def test_resource_exhaustion_handling():
    """Verify system behavior when resources are exhausted"""
    # Intentionally submit more than can fit
    # Verify proper queueing/rejection
    # Check recovery after load decreases
```

## 3. Burst Load Test

```python
@pytest.mark.load
def test_burst_load_recovery():
    """Test system recovery from sudden load spikes"""
    # Normal load -> 10x spike -> normal
    # Measure recovery time, dropped requests
```

## Implementation Guidelines

These would go in `tests/load/` and could:
- Accept failure thresholds (e.g., "95% must complete")
- Output performance metrics
- Run separately from regular CI/CD
- Have different infrastructure requirements