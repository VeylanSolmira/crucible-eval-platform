# Executor ML Image - MVP Implementation

## Overview

This is the MVP solution for supporting ML workloads in the executor service. Instead of complex runtime image selection, we use a single ML-enabled image that can run all workloads.

## What Changed

1. **Created executor-ml Docker image** (`/docker/executor-ml/`)
   - Includes PyTorch 2.0.1 (CPU)
   - Includes Transformers 4.35.0
   - Multi-stage build for security
   - ~1.3GB total size

2. **Updated executor-service**
   - Now uses `EXECUTOR_IMAGE` environment variable
   - Defaults to `python:3.11-slim` if not set
   - No code changes needed for executor logic

3. **Updated docker-compose.yml**
   - Added `executor-ml-image` build target
   - Set `EXECUTOR_IMAGE=executor-ml:latest` for all executors
   - Executors depend on executor-ml-image build

4. **Updated start-platform.sh**
   - Builds executor-ml image automatically
   - Ensures image is available before starting executors

## Usage

### Running ML Code

Now you can run ML workloads directly:

```python
import torch
import transformers

# This now works!
model = pipeline('text-generation', model='distilgpt2')
```

### Testing

Use the test templates:
- `/templates/test_ml_import.py` - Verifies ML libraries are available
- `/templates/hello_world_ml.py` - Simple ML demo

## Security

- Same isolation as before (no network, read-only FS, resource limits)
- Larger image but no runtime flexibility (more secure)
- No user control over image selection

## Future Work

See `/docs/planning/week-5-metr-future-work.md` for the proper multi-image architecture planned for after Kubernetes migration.

## Trade-offs

**Pros:**
- Simple implementation
- Works immediately  
- No security debt
- Easy to migrate later

**Cons:**
- All evaluations use 1.3GB image (even "Hello World")
- Slower cold starts
- More memory usage
- Development friction:
  - ~2-3 minute rebuilds
  - ~30-60 second image pulls
  - Uses significant disk space

This is acceptable for MVP since:
1. Security > Performance
2. We'll fix it properly in K8s
3. Gets us unblocked now

## Quick Workaround for Development

If the 1.3GB image is too painful during development, you can temporarily:

```bash
# In docker-compose.yml, change executor-1's EXECUTOR_IMAGE to:
EXECUTOR_IMAGE=python:3.11-slim

# This will make non-ML code run fast again
# Just remember to test with ML image before pushing
```