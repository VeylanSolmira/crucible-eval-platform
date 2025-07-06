# ML Executor Image

Specialized executor image for machine learning workloads, including PyTorch and Transformers.

## Features

- **PyTorch 2.0.1** (CPU-only to reduce size)
- **Transformers 4.35.0** (Hugging Face)
- Multi-stage build for security (no build tools in final image)
- Offline mode enforced (no network access for model downloads)
- Non-root user execution
- pip and package managers removed from final image

## Security Model

Inherits all security restrictions from base executor, plus:

### ML-Specific Security
- `TRANSFORMERS_OFFLINE=1` - Prevents model downloads during execution
- `HF_DATASETS_OFFLINE=1` - Prevents dataset downloads
- No pip/easy_install in final image
- Build tools (gcc, g++) only in builder stage
- Models must be pre-cached or provided via mounted volumes

### Runtime Restrictions (enforced by executor-service)
- No network access (`--network=none`)
- Read-only filesystem except /tmp
- Memory limit: 512MB (may need adjustment for larger models)
- CPU limit: 0.5 CPU
- Temporary model cache at `/tmp/transformers_cache`

## Usage

### Building

```bash
docker build -t executor-ml:latest .
```

### Example Evaluation Code

```python
# This would work in the ML executor:
from transformers import pipeline

# Note: Model must be pre-cached or this will fail due to offline mode
generator = pipeline('text-generation', model='distilgpt2')
result = generator("Hello, I'm a language model", max_length=30)
print(result)
```

## Model Management

Since the executor runs in offline mode, models must be handled via:

1. **Pre-caching** (uncomment the model download in Dockerfile)
2. **Volume mounts** (mount pre-downloaded models as read-only)
3. **Custom images** (create variants with specific models)

## Resource Considerations

- Base image size: ~500MB (python:3.11-slim)
- PyTorch (CPU): ~700MB
- Transformers: ~50MB
- Total: ~1.3GB

For production, consider:
- Model-specific images (e.g., executor-ml-nlp, executor-ml-vision)
- Shared model cache volumes
- Increased memory limits for larger models
- GPU support (would require different base image and security considerations)

## Future Enhancements

1. **Model Registry Integration**
   ```python
   # Potential model mounting system
   volumes = {
       '/models/distilgpt2': {'bind': '/tmp/models/distilgpt2', 'mode': 'ro'}
   }
   ```

2. **GPU Support** (requires additional security measures)
   - nvidia-docker runtime
   - GPU resource limits
   - CUDA-enabled PyTorch

3. **Additional Frameworks**
   - TensorFlow
   - JAX
   - Scikit-learn
   - Pandas/NumPy for data science

4. **Resource Profiling**
   - Memory usage patterns
   - Optimal CPU allocation
   - Model-specific limits