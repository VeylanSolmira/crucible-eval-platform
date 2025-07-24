# Automatic Resource Cleanup Strategies

This document describes advanced strategies for automatic resource cleanup during tests, beyond the current manual tracking approach.

## Current State vs Automatic Cleanup

### Current Implementation
Tests must explicitly use the resource manager to track resources:

```python
def test_evaluation(api_session, resource_manager):
    eval_id = submit_evaluation(...)
    # Must manually track:
    resource_manager.track_resource("jobs", f"job-{eval_id}")
```

### Automatic Implementation Goals
1. **Label all evaluation pods/jobs** with test identifiers
2. **Auto-discover** resources created during each test
3. **Clean up** based on labels, not manual tracking

## Implementation Strategies

### 1. Test-Level Pytest Hook

Automatically clean up resources after each test using pytest fixtures:

```python
# In conftest.py
@pytest.fixture(autouse=True)
def auto_cleanup(request):
    """Automatically clean up resources after each test."""
    if not should_cleanup(request):
        yield
        return
    
    # Generate unique test ID
    test_id = f"{request.node.name}-{int(time.time())}"
    
    # Set environment variable for API to use
    os.environ["TEST_LABEL_ID"] = test_id
    
    yield  # Test runs here
    
    # Cleanup after test
    cleanup_level = request.config.getoption("--cleanup-level", "pods")
    if cleanup_level != "none":
        # Delete all resources with this test's label
        if cleanup_level in ["pods", "all"]:
            subprocess.run([
                "kubectl", "delete", "pods", "-n", "crucible",
                "-l", f"test-id={test_id}", "--wait=false"
            ])
        if cleanup_level == "all":
            subprocess.run([
                "kubectl", "delete", "jobs", "-n", "crucible", 
                "-l", f"test-id={test_id}", "--wait=false"
            ])
```

### 2. API Modification for Auto-Labeling

Modify job creation to automatically add test labels:

```python
# In celery_runner.py or wherever jobs are created
def create_job_manifest(eval_id, code, ...):
    # Get test ID from environment (if running in test)
    test_id = os.environ.get("TEST_LABEL_ID")
    
    labels = {
        "app": "evaluation",
        "eval-id": eval_id,
    }
    
    if test_id:
        # Add test label if running in test context
        labels["test-id"] = test_id
    
    return {
        "metadata": {
            "labels": labels
        }
        # ... rest of manifest
    }
```

### 3. Time-Based Cleanup

Clean up old resources without requiring API changes:

```python
@pytest.fixture(autouse=True, scope="function")
def cleanup_old_resources(request):
    """Clean up resources older than 1 hour."""
    if request.config.getoption("--cleanup-old"):
        # Delete pods older than 1 hour
        subprocess.run([
            "kubectl", "delete", "pods", "-n", "crucible",
            "-l", "app=evaluation",
            "--field-selector", f"metadata.creationTimestamp<{one_hour_ago}"
        ])
    yield
```

### 4. Resource Pressure Cleanup

Clean up only when resource limits are approached:

```python
def cleanup_if_needed():
    """Clean up only if resource pressure detected."""
    # Check resource quota usage
    quota = get_resource_quota_usage()
    
    if quota["used"]["pods"] > quota["hard"]["pods"] * 0.8:
        # Over 80% pod usage, clean up completed pods
        subprocess.run([
            "kubectl", "delete", "pods", "-n", "crucible",
            "-l", "app=evaluation",
            "--field-selector", "status.phase=Succeeded"
        ])
```

### 5. Watermark-Based Cleanup

Sophisticated cleanup with high/low watermarks:

```python
class WatermarkCleaner:
    """Clean up when hitting high watermark, stop at low watermark."""
    
    def __init__(self, high_watermark=0.8, low_watermark=0.5):
        self.high_watermark = high_watermark
        self.low_watermark = low_watermark
    
    def maybe_cleanup(self):
        usage = get_pod_usage_ratio()
        
        if usage > self.high_watermark:
            # Start cleaning oldest pods until we hit low watermark
            while get_pod_usage_ratio() > self.low_watermark:
                delete_oldest_completed_pod()
```

### 6. Interceptor Pattern

Intercept API calls to track resources automatically:

```python
class APIInterceptor:
    """Intercept API calls to track created resources."""
    
    def __init__(self, original_session):
        self.session = original_session
        self.created_resources = []
    
    def post(self, url, **kwargs):
        response = self.session.post(url, **kwargs)
        
        # If this created an evaluation, track it
        if "/eval" in url and response.status_code == 200:
            eval_id = response.json().get("eval_id")
            if eval_id:
                self.created_resources.append(("job", f"evaluation-job-{eval_id}"))
        
        return response
    
    def cleanup_all(self):
        """Clean up all tracked resources."""
        for resource_type, name in self.created_resources:
            # Cleanup logic here
            pass
```

## Pros and Cons

### Pros of Automatic Cleanup
1. **No test modifications needed** - Works with existing tests
2. **Prevents resource leaks** - Even if tests crash
3. **Consistent cleanup** - No forgotten resources
4. **Smart strategies** - Can clean based on age, pressure, etc.

### Cons
1. **Less control** - Tests can't preserve specific resources
2. **API changes needed** - For label-based approaches
3. **Potential race conditions** - Might delete in-progress resources
4. **Debugging harder** - Resources disappear automatically

## Recommended Implementation Path

### Phase 1: Time-Based Cleanup (No API Changes)
- Implement cleanup of resources older than X minutes
- Add as optional pytest flag
- Safe fallback for all environments

### Phase 2: Test Labeling (Minimal API Changes)
- Add optional test-id label to created resources
- Enable precise per-test cleanup
- Maintain backward compatibility

### Phase 3: Smart Strategies (Advanced)
- Implement watermark-based cleanup
- Add resource pressure detection
- Create pluggable cleanup strategies

## Configuration Examples

### Simple Time-Based
```bash
# Clean up resources older than 30 minutes
pytest --cleanup-old --cleanup-age=30m
```

### Label-Based with Fallback
```bash
# Use labels when available, time-based fallback
pytest --auto-cleanup --cleanup-fallback=time
```

### Resource-Aware
```bash
# Clean up when hitting 80% resource usage
pytest --cleanup-strategy=watermark --high-watermark=0.8
```

## Integration with CI/CD

For CI/CD pipelines, combine strategies:

```yaml
- name: Run Tests with Auto Cleanup
  run: |
    pytest \
      --auto-cleanup \
      --cleanup-strategy=hybrid \
      --cleanup-age=15m \
      --high-watermark=0.7
```

## Future Enhancements

1. **Cleanup Policies** - Define per-test or per-suite cleanup rules
2. **Resource Priorities** - Keep important resources longer
3. **Cleanup Metrics** - Track what gets cleaned and why
4. **Dry-Run Mode** - Preview what would be cleaned
5. **Cleanup Hooks** - Custom cleanup logic per resource type

## Conclusion

Automatic cleanup can significantly improve test reliability and resource utilization. Start with simple time-based cleanup and gradually add more sophisticated strategies based on your needs.