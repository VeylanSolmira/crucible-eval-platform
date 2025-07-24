# Adaptive Timeout Strategies for Variable Resource Clusters

When running tests across different Kubernetes clusters with varying resources, tests need to adapt their timeouts programmatically to ensure reliability without excessive waiting. This document outlines several strategies for making tests resource-aware.

## 1. Resource-Aware Timeout Calculation

Calculate timeouts based on available cluster resources:

```python
@pytest.fixture
def adaptive_timeout(api_session):
    """Calculate timeout based on available cluster resources"""
    # Get resource quota
    import subprocess
    import json
    
    # Check available resources
    result = subprocess.run([
        "kubectl", "get", "resourcequota", "evaluation-quota", 
        "-n", "crucible", "-o", "json"
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        quota = json.loads(result.stdout)
        available_memory = (
            int(quota['status']['hard']['limits.memory'].rstrip('Gi')) * 1024 -
            int(quota['status']['used']['limits.memory'].rstrip('Mi'))
        )
        
        # Calculate max concurrent evaluations
        eval_memory = 512  # Mi per evaluation
        max_concurrent = available_memory // eval_memory
        
        # Base timeout + serialization penalty
        base_timeout = 10  # seconds per evaluation
        total_evaluations = 10
        
        if max_concurrent < total_evaluations:
            # Need serialization
            waves = (total_evaluations + max_concurrent - 1) // max_concurrent
            timeout = waves * base_timeout + 10  # +10s for scheduling overhead
        else:
            # Can run fully parallel
            timeout = base_timeout + 10
            
        return timeout
    
    # Fallback to safe default
    return 60
```

## 2. Progress-Based Dynamic Timeout

Extend timeouts dynamically as long as progress is being made:

```python
def wait_for_evaluations_with_progress(
    api_session, eval_ids, min_progress_interval=10.0
):
    """
    Wait for evaluations with dynamic timeout based on progress.
    Keeps extending timeout as long as progress is being made.
    """
    completed = set()
    last_progress_time = time.time()
    
    while len(completed) < len(eval_ids):
        # Check all evaluations
        made_progress = False
        
        for eval_id in eval_ids:
            if eval_id not in completed:
                response = api_session.get(f"{api_base_url}/eval/{eval_id}")
                if response.status_code == 200:
                    result = response.json()
                    if result["status"] in ["completed", "failed", "timeout"]:
                        completed.add(eval_id)
                        made_progress = True
        
        if made_progress:
            last_progress_time = time.time()
        elif time.time() - last_progress_time > min_progress_interval:
            # No progress in min_progress_interval seconds
            remaining = set(eval_ids) - completed
            pytest.fail(f"No progress in {min_progress_interval}s. "
                       f"Stuck evaluations: {list(remaining)[:5]}")
        
        time.sleep(0.5)
    
    return completed
```

## 3. Benchmark-Based Calibration

Run a calibration test to determine cluster performance:

```python
@pytest.fixture(scope="session")
def performance_multiplier(api_session, api_base_url):
    """
    Run a calibration test to determine cluster performance.
    Returns a multiplier for timeouts.
    """
    # Submit a simple benchmark evaluation
    start = time.time()
    response = api_session.post(
        f"{api_base_url}/eval",
        json={"code": "print('benchmark')", "language": "python"}
    )
    eval_id = response.json()["eval_id"]
    
    # Wait for completion
    while time.time() - start < 30:
        response = api_session.get(f"{api_base_url}/eval/{eval_id}")
        if response.json()["status"] in ["completed", "failed"]:
            elapsed = time.time() - start
            
            # Compare to baseline (e.g., 3 seconds on reference cluster)
            baseline = 3.0
            multiplier = max(1.0, elapsed / baseline)
            
            return multiplier
        time.sleep(0.1)
    
    # Timeout on benchmark = very slow cluster
    return 3.0  # 3x multiplier
```

## 4. Configuration-Based Approach

Define cluster profiles based on available resources:

```python
# In conftest.py
@pytest.fixture
def cluster_profile():
    """Get cluster profile from environment or auto-detect"""
    import os
    
    profile = os.getenv("CLUSTER_PROFILE", "auto")
    
    if profile == "auto":
        # Auto-detect based on node resources
        result = subprocess.run([
            "kubectl", "get", "nodes", "-o", 
            "jsonpath={.items[*].status.capacity.memory}"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            # Parse memory (e.g., "16Gi" -> 16)
            memory_gb = int(result.stdout.strip().rstrip("Gi"))
            
            if memory_gb < 8:
                profile = "constrained"
            elif memory_gb < 32:
                profile = "standard"
            else:
                profile = "powerful"
    
    profiles = {
        "constrained": {"timeout_multiplier": 2.0, "max_concurrent": 5},
        "standard": {"timeout_multiplier": 1.0, "max_concurrent": 10},
        "powerful": {"timeout_multiplier": 0.5, "max_concurrent": 20}
    }
    
    return profiles.get(profile, profiles["standard"])
```

## 5. Integrated Adaptive Test Example

Combining multiple strategies for robust testing:

```python
@pytest.mark.slow
def test_concurrent_with_adaptive_timeout(
    api_session, api_base_url, adaptive_timeout, performance_multiplier
):
    """Test with dynamically calculated timeout"""
    num_evaluations = 10
    
    # Submit evaluations
    eval_ids = submit_evaluation_batch(
        api_session, api_base_url,
        [f'print("test {i}")' for i in range(num_evaluations)]
    )
    
    # Calculate timeout
    timeout = adaptive_timeout * performance_multiplier
    print(f"Using adaptive timeout: {timeout}s "
          f"(base: {adaptive_timeout}, multiplier: {performance_multiplier})")
    
    # Wait with progress tracking
    completed = wait_for_evaluations_with_progress(
        api_session, eval_ids, 
        min_progress_interval=timeout/6  # No progress for 1/6 of total time
    )
    
    assert len(completed) == num_evaluations
```

## Best Practices

1. **Combine Strategies**: Use resource discovery for initial calculation, then apply performance multipliers
2. **Progress Tracking**: Avoid unnecessary waiting by tracking actual progress
3. **Environment Variables**: Allow manual overrides via environment variables
4. **Logging**: Always log the calculated timeouts for debugging
5. **Fallback Values**: Have sensible defaults when resource detection fails

## Implementation Order

1. Start with simple timeout multipliers from environment variables
2. Add resource-based calculation for memory constraints
3. Implement progress tracking to avoid excessive waits
4. Add performance calibration for new clusters
5. Create cluster profiles for known environments

These strategies ensure tests remain reliable across different environments while minimizing unnecessary wait times.