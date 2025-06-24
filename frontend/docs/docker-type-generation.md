# Docker Type Generation Strategies

## The Challenge

When building a frontend Docker image, you might want to generate TypeScript types from the API's OpenAPI spec. However, this creates a chicken-and-egg problem:

- The API needs to be running to serve the OpenAPI spec
- But during `docker build`, other services aren't available
- Multi-stage builds run in isolation

## Solutions

### 1. Generate Types Locally, Commit to Repo (Recommended)

**Pros:**
- Simple and reliable
- Types are versioned with your code
- No runtime dependencies during build
- CI/CD can verify types match

**Process:**
```bash
# Locally with services running
npm run generate-types

# Commit the generated types
git add types/generated/api.ts
git commit -m "Update API types"
```

**Dockerfile:**
```dockerfile
# Types are already in the repo, just copy them
COPY types ./types
```

### 2. Generate Types in CI/CD Pipeline

**Pros:**
- Always fresh types
- Can fail build if API contract changed

**GitHub Actions Example:**
```yaml
- name: Start services
  run: docker-compose up -d api-service

- name: Wait for API
  run: sleep 5

- name: Generate types
  run: npm run generate-types

- name: Build frontend
  run: docker build -t frontend .
```

### 3. Multi-Stage Build with Network (Complex)

**Pros:**
- Self-contained build
- Always uses latest API

**Cons:**
- Complex Docker setup
- Requires Docker BuildKit
- Build depends on external service

**Example:**
```dockerfile
# This requires BuildKit and special build commands
FROM node:20 AS types
RUN --network=host npm run generate-types:docker
```

### 4. Generate During Container Startup (Not Recommended)

**Pros:**
- Always matches running API

**Cons:**
- Slower startup
- Runtime dependency
- Can fail in production

**Example:**
```dockerfile
# In entrypoint script
npm run generate-types:docker && npm start
```

## When to Use `generate-types:docker`

The `generate-types:docker` variant is useful when:

1. **Development in Containers**: If you develop inside a container:
   ```bash
   docker exec frontend-dev npm run generate-types:docker
   ```

2. **Docker Compose Override**: For local development:
   ```yaml
   # docker-compose.override.yml
   services:
     frontend:
       command: >
         sh -c "npm run generate-types:docker && npm run dev"
   ```

3. **Integration Tests**: Generate types in test containers:
   ```bash
   docker run --network=myapp_default \
     frontend-test npm run generate-types:docker
   ```

## Recommendation

For most projects, **Option 1** (generate locally, commit to repo) is best because:

1. **Predictable Builds**: No external dependencies during build
2. **Version Control**: Types are tracked with code changes
3. **PR Review**: API changes are visible in pull requests
4. **Fast Builds**: No need to start services during build
5. **Offline Builds**: Can build without network access

The `generate-types:docker` command exists for special cases where you need to generate from within the Docker network, but it shouldn't be part of your standard build process.