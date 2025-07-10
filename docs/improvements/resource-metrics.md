# Resource Metrics Display Issue

## Current Problem
The ExecutionMonitor component shows CPU and Memory usage, but they're always at 0. The frontend expects these fields but the backend never sends them.

## Why It's Broken
1. The executor-service doesn't collect container stats
2. Docker stats API requires polling the container
3. The log streaming endpoint only returns output, not metrics

## Quick Fix Options

### Option 1: Hide the Metrics (5 minutes)
Simply hide the CPU/Memory display in ExecutionMonitor until we implement it properly.

### Option 2: Basic Implementation (1-2 hours)
```python
# In executor-service, add stats collection:
def get_container_stats(container):
    """Get CPU and memory usage from container"""
    try:
        stats = container.stats(stream=False)
        # Parse stats['memory_stats'] and stats['cpu_stats']
        return {
            'memory_usage': stats['memory_stats']['usage'] / 1024 / 1024,  # MB
            'cpu_percent': calculate_cpu_percent(stats)
        }
    except:
        return {'memory_usage': 0, 'cpu_percent': 0}
```

### Option 3: Wait for Kubernetes (Recommended)
In Kubernetes, resource metrics are much easier:
- Built-in metrics server
- Standard resource monitoring
- No need to poll individual containers

## Impact on Demos
- CPU exhaustion demo: Can't show actual CPU usage (but throttling still works)
- Memory exhaustion demo: Can't show memory climbing before OOM
- Basic demos: Metrics display looks broken

## Recommendation
**Hide the metrics display for now** rather than showing zeros. Add a note that resource monitoring is "coming soon with Kubernetes migration."

This avoids:
- Implementing temporary Docker stats polling
- Complex metric calculation code
- Performance overhead of stats API

The demos still work to show resource limits are enforced, just without real-time metrics.