# OpenAPI Generation Optimization

## Problem

When the API service is modified and rebuilt, the OpenAPI spec files are regenerated even if the API contract hasn't changed. This causes:

1. New file timestamps on `openapi.json` and `openapi.yaml`
2. Frontend rebuild triggered due to "changed" dependencies
3. Unnecessary Docker layer invalidation
4. Longer build times for no actual changes

## Current Behavior

```bash
# Current flow:
1. API code changes (e.g., internal health check logic)
2. ./scripts/build-and-push-images.sh runs
3. generate-all-openapi-specs.sh regenerates ALL specs
4. Frontend sees "new" openapi.yaml (different timestamp)
5. Frontend rebuilds entirely, including type generation
```

## Proposed Solutions

### 1. Content-Based Comparison (Recommended)

Before writing the new OpenAPI spec, compare it with the existing file:

```python
# In export-openapi-spec.py
import json
import hashlib

# Generate new spec
openapi_schema = app.openapi()
new_content = json.dumps(openapi_schema, indent=2, sort_keys=True)

# Compare with existing
if json_path.exists():
    with open(json_path, "r") as f:
        existing_content = json.load(f)
    existing_json = json.dumps(existing_content, indent=2, sort_keys=True)
    
    if existing_json == new_content:
        print(f"✅ OpenAPI spec unchanged, skipping write")
        return

# Only write if changed
with open(json_path, "w") as f:
    f.write(new_content)
```

**Pros:**
- Simple to implement
- Preserves timestamps when content unchanged
- Works with existing build system
- No changes to frontend needed

**Cons:**
- Requires reading file before writing
- Need to ensure consistent formatting

### 2. Deterministic Generation

Ensure the output is always identical for the same API definition:

```python
# Remove volatile fields
openapi_schema = app.openapi()
openapi_schema.pop('info.version', None)  # Remove version timestamps
openapi_schema.pop('servers', None)  # Remove environment-specific servers

# Always sort keys
json.dump(openapi_schema, f, indent=2, sort_keys=True)
yaml.dump(openapi_schema, f, sort_keys=True)
```

**Pros:**
- Git diffs are cleaner
- Reproducible builds

**Cons:**
- May lose useful metadata
- Still writes file each time

### 3. Separate Generation from Build

Move OpenAPI generation out of the build process:

```bash
# Only generate when API actually changes
# Option 1: Git pre-commit hook
.git/hooks/pre-commit:
  if git diff --cached --name-only | grep -q "api/.*\.py"; then
    ./scripts/generate-api-openapi-spec.sh
  fi

# Option 2: Manual trigger
make update-openapi  # Run only when API changes

# Option 3: CI/CD only on API changes
- name: Generate OpenAPI
  if: contains(github.event.head_commit.modified, 'api/')
```

**Pros:**
- Fastest builds (no generation)
- Clear separation of concerns

**Cons:**
- Risk of forgetting to generate
- Can lead to out-of-sync specs

### 4. Docker Layer Optimization

Structure Dockerfile to cache type generation:

```dockerfile
# Frontend Dockerfile
# Copy only OpenAPI specs first
COPY api/openapi.yaml ./api/
COPY storage_service/openapi.yaml ./storage_service/

# Generate types (this layer caches if specs unchanged)
RUN npm run generate-types

# Then copy source code
COPY . .

# Build (uses cached types if possible)
RUN npm run build
```

**Pros:**
- Works even if timestamps change
- Docker handles caching

**Cons:**
- Only helps with Docker builds
- Requires Dockerfile restructuring

### 5. Build Tool Integration

Use content-aware build tools:

```json
// turbo.json or nx.json
{
  "pipeline": {
    "generate-types": {
      "inputs": ["../api/openapi.yaml"],
      "outputs": ["types/generated/**"],
      "cache": true  // Cache based on content hash
    }
  }
}
```

**Pros:**
- Automatic content-based caching
- Handles complex dependency graphs

**Cons:**
- Requires adopting new build tools
- More complex setup

### 6. Checksum Files

Generate checksums alongside specs:

```bash
# After generating openapi.yaml
sha256sum api/openapi.yaml > api/openapi.yaml.sha256

# Frontend checks checksum before regenerating
if [ "$(cat api/openapi.yaml.sha256)" != "$(sha256sum api/openapi.yaml)" ]; then
  npm run generate-types
fi
```

**Pros:**
- Explicit tracking of changes
- Can skip entire generation step

**Cons:**
- More files to manage
- Additional build complexity

## Recommendation

Implement **Solution #1 (Content-Based Comparison)** as it:
- Requires minimal changes
- Solves the immediate problem
- Maintains compatibility with existing build system
- Can be implemented quickly

Later, consider Docker layer optimization for additional build speed improvements.

## Implementation Steps

1. Update `export-openapi-spec.py` scripts to compare before writing
2. Ensure consistent JSON/YAML formatting (sort_keys=True)
3. Test that unchanged APIs don't trigger rebuilds
4. Apply same pattern to storage_service OpenAPI generation
5. Document the new behavior

## Expected Outcome

- API-only changes won't trigger frontend rebuilds
- Faster build times
- Reduced Docker image layer churn
- More efficient CI/CD pipelines