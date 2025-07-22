# Executor Image Resolution Design

## Overview
This document outlines the design for resolving executor images (like `executor-ml`) at runtime in both development and production environments.

## The Challenge
- **Build time**: Skaffold knows the SHA-tagged images but can't easily pass them to runtime
- **Runtime**: Dispatcher needs image names, but executor images aren't part of any deployment
- **Executor images**: Only used for creating Jobs, not present in any service/deployment

## Proposed Solution

### Development/Local Environment
**Query node images directly**

```python
# Dispatcher queries Kubernetes nodes for images
def get_latest_executor_image(executor_type: str) -> str:
    """Find the most recent executor image from node image store"""
    # Query nodes API for images matching pattern
    images = v1.list_node().items[0].status.images
    executor_images = [img for img in images if f"executor-{executor_type}" in img.names[0]]
    # Return most recent (first in list)
    return executor_images[0].names[0]
```

**Benefits**:
- Simple, no coordination needed
- Works naturally with Skaffold's SHA tags
- No extra infrastructure
- Automatic updates with each build

### Production Environment
**Lightweight Executor Registry Service**

A dedicated service that maintains a catalog of available executor images:

1. **Watches container registry** (ECR/GCR) for `executor-*` tagged images
   - Via registry webhooks or periodic polling
   - Validates images meet security requirements

2. **Maintains a catalog**:
   ```json
   {
     "ml": {
       "image": "123456789.dkr.ecr.us-west-2.amazonaws.com/executor-ml:sha256:abc123",
       "capabilities": ["pytorch", "cuda"],
       "added": "2024-01-10T10:30:00Z",
       "validated": true
     },
     "custom-nlp": {
       "image": "123456789.dkr.ecr.us-west-2.amazonaws.com/executor-nlp:sha256:def456", 
       "capabilities": ["transformers", "spacy"],
       "owner": "nlp-team",
       "added": "2024-01-10T11:00:00Z"
     }
   }
   ```

3. **Minimal API**:
   ```yaml
   GET /executors              # List all available executors
   GET /executors/{type}       # Get specific executor details
   POST /executors/refresh     # Force registry scan
   GET /health                 # Health check
   ```

4. **Implementation details**:
   - Start with in-memory storage
   - Add Redis/PostgreSQL persistence if needed
   - Include caching with TTL
   - Support for versioning/canary deployments later

### Dispatcher Integration

```python
class ExecutorResolver:
    def __init__(self, environment: str):
        self.environment = environment
        
    async def get_executor_image(self, executor_type: str) -> str:
        if self.environment == "development":
            # Query node images directly
            return self.get_latest_node_image(executor_type)
        else:
            # Query executor registry service
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{EXECUTOR_REGISTRY_URL}/executors/{executor_type}")
                return resp.json()["image"]
```

## Alternative Considered: ConfigMap Approach

For production, we also considered using ConfigMaps with explicit versions:
- ConfigMap specifies exact image tags
- Updated through CI/CD pipeline or GitOps
- Simpler but less flexible than registry service

## Why This Design

### Development
- No fighting with build tools
- Natural workflow with Skaffold
- Zero configuration needed
- Immediate availability of new builds

### Production
- **Single source of truth** for available executors
- **Dynamic addition** without redeploying services
- **Security validation** before images are available
- **Natural extension point** for:
  - Versioning strategies
  - Canary deployments
  - A/B testing
  - Usage metrics
  - Cost allocation

### Trade-offs
- **Pro**: Clean separation of concerns
- **Pro**: Flexibility for future requirements
- **Pro**: Works with existing tooling
- **Con**: One more service in production
- **Con**: Additional operational complexity

## Implementation Plan

### Phase 1: Local Development (1 day)
- [ ] Update dispatcher to query node images
- [ ] Remove ConfigMap-based approach
- [ ] Test with Skaffold dev workflow

### Phase 2: Registry Service MVP (2-3 days)
- [ ] Create FastAPI service skeleton
- [ ] Implement ECR/GCR polling
- [ ] Add basic API endpoints
- [ ] Deploy to staging

### Phase 3: Production Hardening (1 week)
- [ ] Add persistence layer
- [ ] Implement caching
- [ ] Add monitoring/alerting
- [ ] Security scanning integration
- [ ] Documentation

## Deployment Considerations

### Local (Kind)
- No changes needed
- Dispatcher queries node images directly

### Production (EKS/GKE)
- Deploy executor-registry as a Deployment
- Service exposed internally only
- RBAC for registry access
- Network policies for security

## Security Considerations
- Registry service validates image signatures
- Only approved namespaces can push executor images
- Audit log for all executor additions
- Regular vulnerability scanning

## Future Extensions
- Executor capability discovery
- Resource requirement hints
- Cost estimation per executor type
- Usage analytics dashboard