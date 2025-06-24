# Dynamic OpenAPI Generation Patterns for Read-Only Containers

## Context
When running API containers with read-only filesystems (a security best practice), generating OpenAPI specifications at runtime becomes challenging. The API can't write the spec to its own filesystem.

## Proposed Solutions

### 1. Init Container Pattern

Uses a separate container to generate the spec into a shared volume before the API starts.

```yaml
# docker-compose.yml
services:
  # Init container that generates the spec
  api-spec-generator:
    build: ./api
    command: python -c "
      from app.main import app;
      import yaml;
      with open('/specs/openapi.yaml', 'w') as f:
        yaml.dump(app.openapi(), f);
      print('✅ Generated OpenAPI spec')
      "
    volumes:
      - api-specs:/specs
    # Run once and exit
    restart: "no"

  api:
    build: ./api
    ports:
      - "8000:8000"
    read_only: true
    tmpfs:
      - /tmp
    volumes:
      - api-specs:/specs:ro  # Read-only access to specs
    depends_on:
      api-spec-generator:
        condition: service_completed_successfully
    environment:
      - STATIC_SPEC_PATH=/specs/openapi.yaml

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - api-specs:/specs:ro  # Frontend can also read the spec
    depends_on:
      - api-spec-generator
    environment:
      - OPENAPI_SPEC_PATH=/specs/openapi.yaml

volumes:
  api-specs:
```

**Pros:**
- Spec always fresh on container start
- Clean separation of concerns
- Shared volume works well for multi-service access
- API container remains fully read-only

**Cons:**
- Additional container startup time
- Volume management complexity
- Potential race conditions if API changes during runtime
- Spec only updated on container restart

### 2. Multi-stage Startup with Entrypoint

Generates the spec during container startup using an entrypoint script.

```dockerfile
# api/Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Create entrypoint that generates spec before starting server
RUN echo '#!/bin/sh\n\
python -c "from app.main import app; import yaml; \
import os; os.makedirs("/specs", exist_ok=True); \
with open("/specs/openapi.yaml", "w") as f: \
  yaml.dump(app.openapi(), f)" && \
exec "$@"' > /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

```yaml
# docker-compose.yml
services:
  api:
    build: ./api
    ports:
      - "8000:8000"
    read_only: true
    tmpfs:
      - /tmp
      - /specs  # Writable tmpfs for spec generation
    volumes:
      - api-specs:/specs
    
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - api-specs:/specs:ro
    depends_on:
      - api

volumes:
  api-specs:
```

**Pros:**
- Single container, simpler deployment
- Guarantees spec exists before API starts
- No additional containers to manage

**Cons:**
- Mixes concerns (spec generation + API serving)
- Still needs writable location (tmpfs)
- Spec regenerated on every restart (performance impact)
- Entrypoint complexity

### 3. Dedicated Spec Service (Recommended)

A lightweight service that only serves the OpenAPI specification.

```python
# api/spec_server.py
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
import yaml
import os
from app.main import app as main_app

spec_app = FastAPI()

# Generate spec on startup
spec_data = main_app.openapi()

@spec_app.get("/openapi.yaml")
async def get_yaml_spec():
    return Response(
        content=yaml.dump(spec_data),
        media_type="application/x-yaml",
        headers={"Cache-Control": "public, max-age=3600"}
    )

@spec_app.get("/openapi.json")
async def get_json_spec():
    return JSONResponse(spec_data)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(spec_app, host="0.0.0.0", port=8001)
```

```yaml
# docker-compose.yml
services:
  api:
    build: ./api
    ports:
      - "8000:8000"
    read_only: true
    tmpfs:
      - /tmp
    command: uvicorn app.main:app --host 0.0.0.0

  spec-server:
    build: ./api
    ports:
      - "8001:8001"
    read_only: true
    tmpfs:
      - /tmp
    command: python spec_server.py
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/openapi.yaml"]
      interval: 30s
      timeout: 3s
      retries: 3

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - API_URL=http://api:8000
      - SPEC_URL=http://spec-server:8001/openapi.yaml
    depends_on:
      spec-server:
        condition: service_healthy
```

**Pros:**
- Keeps API container fully read-only
- Provides a clean HTTP interface
- Works well with frontend tooling
- Can serve multiple formats (YAML/JSON)
- Easy to health check
- No filesystem coordination needed
- Could add caching, versioning, or change detection
- Clean architectural separation

**Cons:**
- Another service to manage
- Additional network hop
- Slight increase in complexity
- More resource usage (additional container)

## Comparison with Current Approach

### Current Implementation (Static + CI/CD)
- Static `api/openapi.yaml` file in repository
- Manual updates via `scripts/update-openapi-spec.sh`
- GitHub Actions generates artifacts on API changes
- Frontend Docker builds use static file

**Pros:**
- Simple and predictable
- No runtime overhead
- Version controlled
- Works with read-only containers

**Cons:**
- Manual step required for local development
- Can drift from actual API
- Requires discipline to keep updated

### Dynamic Generation Benefits
- Always in sync with API code
- No manual steps
- Better for rapid API development
- Impossible to have drift

### Dynamic Generation Drawbacks
- Runtime complexity
- Additional services/volumes
- Potential startup delays
- More points of failure

## Hybrid Approach Recommendation

Use different strategies for different environments:

```yaml
# docker-compose.yml (dev)
services:
  spec-server:
    build: ./api
    command: python spec_server.py
    ports:
      - "8001:8001"
    profiles: ["dev"]  # Only in development

  api:
    # ... normal config ...

  frontend:
    environment:
      # In dev: use spec server, in prod: use static file
      - OPENAPI_URL=${OPENAPI_URL:-http://spec-server:8001/openapi.yaml}
```

- **Development**: Use spec server for automatic updates
- **CI/CD**: Generate static artifacts
- **Production**: Use pre-generated static specs

## Decision Factors

Choose **dynamic generation** when:
- API is changing frequently
- Multiple teams consuming the spec
- Real-time accuracy is critical
- Development velocity is priority

Choose **static generation** when:
- API is stable
- Deployment simplicity is important
- Minimizing runtime dependencies
- Version control of specs is required

## Implementation Priority

For the current project phase:
1. Keep static generation as primary approach
2. Implement spec server as development tool
3. Evaluate after more API iteration
4. Consider for production if proves valuable

## Related Documentation
- [OpenAPI Integration Guide](../implementation/OPENAPI_INTEGRATION.md)
- [Frontend Type Generation](../../frontend/docs/handling-generated-types.md)
- [API Design Patterns](./api-design-considerations.md)