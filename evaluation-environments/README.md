# Docker Images for Crucible Platform

This directory contains specialized Docker images for the Crucible platform's secure code execution system.

## Image Hierarchy

```
executor-base/          # Minimal Python 3.11 environment
└── executor-ml/       # Adds PyTorch, Transformers for ML workloads
```

## Security Architecture

All executor images follow a defense-in-depth security model:

### Image-Level Security
- Multi-stage builds (build tools don't reach production)
- Non-root user execution
- No package managers in final images
- Minimal attack surface
- Pinned dependencies

### Runtime Security (Enforced by executor-service)
- Network isolation (`--network=none`)
- Read-only filesystem (`--read-only`)
- Resource limits (CPU, memory)
- No new privileges (`--security-opt=no-new-privileges`)
- Temporary storage only (`/tmp` as tmpfs)

### Docker Proxy Security
The executor-service connects through a Docker socket proxy that only allows:
- Container creation, start, stop, removal
- Image listing/inspection
- No exec, volumes, networks, or builds

## Available Images

### executor-base
- **Purpose**: General Python code execution
- **Size**: ~150MB
- **Use Case**: Simple scripts, basic computations
- **Base**: python:3.11-slim

### executor-ml
- **Purpose**: Machine learning workloads
- **Size**: ~1.3GB
- **Frameworks**: PyTorch 2.0.1, Transformers 4.35.0
- **Use Case**: NLP models, neural networks
- **Restrictions**: Offline mode (no model downloads during execution)

## Building Images

```bash
# Build all images
docker build -t executor-base:latest executor-base/
docker build -t executor-ml:latest executor-ml/

# Verify builds
docker images | grep executor
```

## Integration with Executor Service

To use these images, update the executor service configuration:

```python
# In executor-service/app.py
EXECUTOR_IMAGES = {
    'default': 'executor-base:latest',
    'ml': 'executor-ml:latest',
}

# Select image based on evaluation requirements
image = EXECUTOR_IMAGES.get(eval_type, EXECUTOR_IMAGES['default'])
```

## Future Images

Planned specialized images:

### executor-scientific
- NumPy, SciPy, Pandas
- Matplotlib (headless)
- Jupyter kernel support

### executor-web
- Requests, BeautifulSoup
- Async libraries (aiohttp)
- API testing tools

### executor-gpu
- CUDA-enabled PyTorch
- GPU resource management
- Additional isolation measures

## Production Considerations

1. **Image Registry**
   - Push to private registry (ECR)
   - Implement image signing
   - Vulnerability scanning

2. **Model Management**
   - Pre-cache common models
   - Read-only model volumes
   - Model versioning strategy

3. **Resource Optimization**
   - Image layer caching
   - Shared base layers
   - Regular cleanup of unused images

4. **Security Hardening**
   - Regular dependency updates
   - CVE monitoring
   - Distroless variants for production

## Development Workflow

1. Create new image directory
2. Define Dockerfile with security in mind
3. Document security model and use cases
4. Test with executor service
5. Add to CI/CD pipeline

## CI/CD Integration

```yaml
# Example GitHub Actions workflow
- name: Build Executor Images
  run: |
    docker build -t executor-base:latest docker/executor-base/
    docker build -t executor-ml:latest docker/executor-ml/
    
- name: Security Scan
  run: |
    trivy image executor-base:latest
    trivy image executor-ml:latest
```