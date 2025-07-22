# Kubernetes Job Monitoring Tests Migration

## Overview

This document outlines the migration strategy for transforming Docker event diagnostic tests into Kubernetes-native job monitoring tests. The original tests were designed to diagnose Docker-specific race conditions, but in Kubernetes we need different testing approaches.

## Original Docker Event Diagnostics

The Docker event diagnostic tests (`test_docker_event_diagnostics.py`) were created to diagnose:

1. **Race conditions** - Containers exiting before logs could be captured
2. **Event timing** - How quickly Docker events were processed
3. **Container removal** - Containers being removed too quickly after completion
4. **Log retrieval** - Ensuring stdout/stderr were captured from fast-failing containers

These issues were specific to Docker's event system and container lifecycle management.

## Kubernetes Architecture Differences

In Kubernetes, the architecture is fundamentally different:

- **No Docker events** - Kubernetes uses Job status API instead
- **Jobs persist** - Unlike Docker containers, Jobs remain after completion
- **Polling-based** - Celery polls every 10 seconds (vs instant Docker events)
- **Different race conditions** - New timing challenges specific to Kubernetes

## Proposed Test Evolution

### 1. Kubernetes Job Lifecycle Monitoring Tests

Transform container lifecycle tests into Job lifecycle tests:

```python
def test_job_lifecycle_timing(self):
    """Measure latency at each stage of job lifecycle"""
    # Track timestamps for:
    # - Evaluation submitted to API
    # - Celery task created
    # - Kubernetes Job created
    # - Pod scheduled
    # - Pod running
    # - Pod completed
    # - Status updated in storage
    # - Status available via API
    
    # Assert reasonable latencies at each stage
    # Identify bottlenecks in the pipeline
```

### 2. Status Update Latency Tests

Replace event timing tests with status update latency measurements:

```python
def test_status_update_latency(self):
    """Measure time from job state change to user-visible status update"""
    # Submit evaluation
    # Monitor both:
    #   - Kubernetes API (ground truth)
    #   - Storage service (what user sees)
    # Measure lag between actual state and reported state
    # Current: ~10-15 seconds due to Celery polling
    # Future: <1 second with event-driven architecture
```

### 3. Pod Log Streaming Tests

Evolve log retrieval tests for Kubernetes:

```python
def test_fast_failing_job_logs(self):
    """Verify logs are captured from jobs that fail immediately"""
    # Submit code that fails instantly (syntax error, import error, etc.)
    # Verify:
    #   - Both stdout and stderr are captured
    #   - Exit codes are properly recorded
    #   - Logs are available even for <1 second executions
    
def test_log_streaming_reliability(self):
    """Test streaming logs from long-running jobs"""
    # Submit job that outputs continuously
    # Verify:
    #   - Logs are streamed in near real-time
    #   - Large outputs are handled correctly
    #   - Disconnection/reconnection scenarios work
```

### 4. Concurrent Job Monitoring Tests

Replace concurrent container tests with Job monitoring tests:

```python
def test_concurrent_job_monitoring(self):
    """Verify system handles many simultaneous jobs"""
    # Submit 50+ evaluations simultaneously
    # Track all state transitions
    # Verify:
    #   - No status updates are missed
    #   - All jobs complete successfully
    #   - System maintains consistency under load
    #   - Resource quotas are respected
```

### 5. Event-Driven Architecture Tests (Future)

Prepare for future Kubernetes informer implementation:

```python
def test_kubernetes_informer_events(self):
    """Test real-time job event processing (when implemented)"""
    # Submit evaluation
    # Verify events are received for:
    #   - Job created
    #   - Pod scheduled
    #   - Pod running
    #   - Pod completed/failed
    # Measure latency: should be <100ms per event
    
def test_informer_reconnection(self):
    """Test informer handles disconnections gracefully"""
    # Start watching jobs
    # Simulate network interruption
    # Verify no events are lost during reconnection
```

## Implementation Strategy

### Phase 1: Refactor Existing Tests (Current)
1. Update test file with Kubernetes-focused tests
2. Remove Docker-specific assumptions
3. Add appropriate timeouts for Kubernetes timing
4. Focus on integration testing of the full pipeline

### Phase 2: Add Latency Metrics
1. Instrument tests to measure latencies
2. Create performance baselines
3. Add regression tests for performance
4. Document expected timings

### Phase 3: Prepare for Event-Driven (Future)
1. Create interface for swappable monitoring backends
2. Write tests that work with both polling and events
3. Add feature flags for event-driven mode
4. Benchmark improvements when implemented

## Test Organization

Rename and reorganize the test file:

```
tests/integration/test_docker_event_diagnostics.py
→ tests/integration/test_kubernetes_job_monitoring.py
```

Split into focused test classes:
- `TestJobLifecycle` - Job state transition tests
- `TestStatusLatency` - Timing and performance tests  
- `TestLogCapture` - Log retrieval and streaming tests
- `TestConcurrentJobs` - Load and concurrency tests

## Success Criteria

The migrated tests should:

1. **Be Kubernetes-native** - Use Job/Pod APIs, not Docker concepts
2. **Measure the right things** - Focus on user-visible latencies
3. **Guide optimization** - Identify bottlenecks in the system
4. **Support evolution** - Work with both polling and future event-driven approaches
5. **Provide insights** - Help understand system behavior under various conditions

## Key Metrics to Track

- **Submission to Running**: Time from API call to pod execution
- **Completion to Storage**: Time from pod completion to database update  
- **End-to-end Latency**: Total time from submission to final status
- **Log Availability**: Time until logs are accessible
- **Concurrent Capacity**: Number of simultaneous jobs handled

## Related Documentation

- [Event-Based Status Updates Architecture](../architecture/event-based-status-updates.md)
- [Kubernetes Test Architecture Analysis](./kubernetes-test-architecture-analysis.md)
- [Production Testing Strategy](./production-testing-strategy.md)