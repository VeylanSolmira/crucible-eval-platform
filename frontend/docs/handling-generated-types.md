# Handling Generated Types in CI/CD

## Problem Statement

The frontend uses TypeScript types generated from the API's OpenAPI specification. These types are:

- Generated using `openapi-typescript`
- Located at `frontend/types/generated/api.ts`
- Currently in `.gitignore` (best practice for generated files)
- Required during the `npm run build` step

The challenge: How to handle these generated types during Docker builds in CI/CD?

## Professional Approaches

### Option 1: Build-Time Generation (Chosen Solution) ✅

Generate types during Docker build from the OpenAPI spec in the repository.

**Implementation**: Multi-stage Dockerfile that generates types before building the frontend.

**Pros:**

- Always in sync with API spec
- No manual steps required
- No generated files in git
- Self-contained build process
- Works well when frontend and API are in same repo

**Cons:**

- Slightly more complex Dockerfile
- Requires OpenAPI spec to be available during build

**Best for:** Monorepos where frontend and API share a repository.

### Option 2: CI/CD Automation with Commits

Use GitHub Actions to automatically commit updated types when API changes.

**Pros:**

- Simple Docker builds
- Types always available
- Visible history of API changes in git
- Works offline

**Cons:**

- Generated files in version control
- Requires automation setup
- Can create noise in git history

**Best for:** Teams that prefer simplicity over purity.

### Option 3: Pre-build Step in CI/CD

Generate types in CI/CD pipeline before Docker build starts.

**Pros:**

- No generated files in git
- Types always fresh
- Flexible approach

**Cons:**

- More complex CI/CD pipeline
- May require API to be running
- Build artifacts need to be passed between stages

**Best for:** Teams with sophisticated CI/CD infrastructure.

### Option 4: Package Registry Approach

Publish types as an npm package to a registry.

**Pros:**

- Version controlled
- Can be shared across multiple projects
- Clear dependency management

**Cons:**

- Requires package registry infrastructure
- More complex release process
- Additional versioning to manage

**Best for:** Large organizations with multiple frontends consuming the same API.

### Option 5: Runtime Generation (Not Recommended)

Generate types on container startup.

**Pros:**

- Always current
- No build-time complexity

**Cons:**

- Slower startup
- Requires API availability at runtime
- Not suitable for production
- Types not available during build

**Best for:** Development environments only.

## Implementation Details for Option 1

The multistage Dockerfile approach:

1. **Stage 1 - Type Generator**:
   - Uses Node Alpine image
   - Installs `openapi-typescript`
   - Copies OpenAPI spec from API directory
   - Generates TypeScript types

2. **Stage 2 - Dependencies**:
   - Standard dependency installation (unchanged)

3. **Stage 3 - Builder**:
   - Copies generated types from Stage 1
   - Runs normal build process
   - Types are available for TypeScript compilation

4. **Stage 4 - Runner**:
   - Production runtime (unchanged)

## Key Considerations

### Why We Chose Option 1

1. **Same Repository**: Since our frontend and API are in the same repo, we have easy access to the OpenAPI spec
2. **No External Dependencies**: Don't need artifact registries or running services
3. **Reproducible Builds**: Anyone can build the Docker image without setup
4. **Clean Git History**: No generated files cluttering commits

### Trade-offs

- **Build Time**: Slightly longer due to type generation (negligible impact)
- **Complexity**: Multi-stage Dockerfile is more complex but well-documented
- **Coupling**: Frontend build depends on API spec location (acceptable in monorepo)

### Future Considerations

If the architecture changes (e.g., API moves to separate repo), we could:

1. Publish OpenAPI spec to S3/artifact registry
2. Switch to Option 2 (automated commits)
3. Use Option 4 (npm package) for multiple consumers

## Common Pitfalls

1. **Don't forget** to install `openapi-typescript` in the type generator stage
2. **Ensure** the OpenAPI spec path is correct relative to Docker build context
3. **Remember** that generated types are not available in local development without running generation
4. **Avoid** committing generated files accidentally (keep them in .gitignore)

## Known Limitations (To Address Later)

### Build Order Dependency

Currently, the frontend Docker build depends on `api/openapi.yaml` existing:

- **Issue**: Fresh clones don't have this file
- **Workaround**: Run the API service once before building frontend
- **Impact**: CI/CD needs to account for this order
- **Future fix**: Generate spec during API build or commit baseline spec

This is acceptable for development but should be addressed for production CI/CD pipelines.

## Local Development Workflow

When making API changes, developers must update both the OpenAPI spec and TypeScript types:

### Step-by-Step Process

1. **Make API changes** in `api/microservices_gateway.py` (add/modify endpoints)

2. **The OpenAPI spec updates automatically**:
   - When the API service starts, it exports `api/openapi.yaml` and `api/openapi.json`
   - This happens on every container startup
   - No manual step required!

3. **Generate TypeScript types**:

   ```bash
   cd frontend
   npm run generate-types
   ```

   This reads `api/openapi.yaml` and generates `frontend/types/generated/api.ts`

4. **Verify the changes**:
   - Check `api/openapi.yaml` reflects your API changes
   - Check `frontend/types/generated/api.ts` has the new types
   - Ensure frontend code still compiles

5. **Commit together**:
   ```bash
   git add api/microservices_gateway.py api/openapi.yaml
   git commit -m "feat: add new endpoint with OpenAPI spec"
   ```

### Important Notes

- **Always update the spec** when changing the API - it's the contract
- **Never manually edit** `api/openapi.yaml` - it's auto-generated
- **The static spec file** (`api/openapi.yaml`) is the single source of truth
- **Both local and Docker** builds use this same static file
- **CI/CD will fail** if types don't match the API

### Quick Commands

```bash
# After changing API and restarting the service
cd frontend && npm run generate-types

# If you need to manually export the spec (rarely needed)
./scripts/update-openapi-spec.sh

# Before committing API changes
git status  # Should see .py changes (openapi.yaml is auto-generated)
```

### Automated Export Details

The API service automatically exports the OpenAPI spec on startup:

- Location: `api/openapi.yaml` and `api/openapi.json`
- Timing: Every time the API container starts
- Fallback: If PyYAML is missing, only JSON is exported
- Errors: Non-fatal - service continues even if export fails

This ensures the spec is always in sync with the code!

## Conclusion

The build-time generation approach provides the best balance of:

- Clean version control
- Build reproducibility
- Minimal infrastructure requirements
- Type safety

It's particularly well-suited for monorepo architectures where the frontend and API evolve together.
