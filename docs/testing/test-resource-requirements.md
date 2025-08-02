# Test Resource Requirements Guide

## Default Resources (128Mi / 100m CPU)

The default evaluation pod resources have been optimized to 128Mi memory and 100m CPU. This is sufficient for:
- Simple Python scripts
- Basic computations
- Tests that don't import heavy ML frameworks
- Most integration tests

## Tests Requiring Higher Resources

### ML Framework Tests (1Gi+ / 500m CPU)
Tests that import ML frameworks need significantly more memory:
- `import torch` - Requires 600MB-1GB
- `import tensorflow` - Requires 800MB-1.5GB
- `import transformers` - Requires 500MB+ (plus model loading)

**Example:**
```python
# tests/integration/test_ml_libraries.py
eval_id = submit_evaluation(
    code='import torch; print(torch.__version__)',
    memory_limit="1Gi",  # Override default
    cpu_limit="500m"
)
```

### Data Processing Tests (512Mi+ / 200m CPU)
Tests involving data processing libraries:
- `import pandas` with large datasets
- `import numpy` with large arrays
- Image processing with PIL/OpenCV

### Performance Tests
Tests specifically designed to stress resources should specify limits based on what they're testing:
```python
# Testing memory limits
submit_evaluation(code, memory_limit="24Mi", cpu_limit="50m")

# Testing CPU limits
submit_evaluation(code, memory_limit="256Mi", cpu_limit="2")
```

## Best Practices

1. **Use defaults when possible** - Most tests work fine with 128Mi/100m
2. **Override only when needed** - Specify resources only for tests that actually need them
3. **Test incrementally** - Start with lower resources and increase if OOMKilled
4. **Document requirements** - Add comments explaining why higher resources are needed

## Resource Limit Reference

| Test Type | Memory | CPU | Example |
|-----------|---------|-----|---------|
| Simple Python | 128Mi | 100m | print("hello") |
| NumPy/Pandas | 256-512Mi | 200m | Data processing |
| PyTorch | 1Gi | 500m | import torch |
| TensorFlow | 1.5Gi | 500m | import tensorflow |
| Transformers | 2Gi+ | 1 | Model loading |
| Stress tests | Varies | Varies | Based on test goal |

## Troubleshooting

### OOMKilled
If a test is killed for memory:
1. Check if it imports ML frameworks
2. Increase memory_limit in 256Mi increments
3. Consider if the test really needs those imports

### CPU Throttling
If a test is very slow:
1. Check CPU-intensive operations
2. Increase cpu_limit
3. Consider if the test can be optimized

### Pod Preemption
If test pods are being preempted:
1. Check cluster resource usage
2. Consider reducing service limits further
3. Increase test pod priority class