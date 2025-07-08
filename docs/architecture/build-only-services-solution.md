# Build-Only Services Solution

## Problem

The Crucible Platform has two services that only exist for building Docker images:
- `base` - Base Python image with common dependencies
- `executor-ml-image` - ML libraries for executor containers

These services:
1. Are required during local development to build other images
2. Are NOT needed in production (images are pre-built and pushed to ECR)
3. Have no runtime purpose - they're just build dependencies

## Challenge

When deploying to production:
1. Docker Compose tries to pull ALL services defined in docker-compose.yml
2. These build-only services don't exist in ECR
3. Other services have `depends_on` relationships with these build-only services
4. This causes deployment failures

## Solutions Considered

### 1. Docker Profiles (Attempted)
```yaml
base:
  profiles: ["build"]
```
**Problem**: Services with `depends_on: base` fail validation when the profile isn't active:
```
Error: service "api-service" depends on undefined service "base": invalid compose project
```

### 2. Separate docker-compose.build.yml
Move build-only services to a separate file.
**Problem**: Complicates local development, requires multiple compose commands.

### 3. Override in docker-compose.prod.yml
Override these services to use dummy images.
**Problem**: Adds complexity, requires coordinating multiple files.

### 4. Remove depends_on relationships
Remove all `depends_on: base` entries.
**Problem**: Breaks local development where build order matters.

## Chosen Solution: Exit-on-Start Services

```yaml
base:
  image: ${BASE_IMAGE:-crucible-base}
  build:
    context: .
    dockerfile: shared/docker/base.Dockerfile
  command: "true"  # Exit immediately with success
  restart: "no"   # Never restart
```

### Why This Works

1. **Local Development**:
   - Services build normally
   - Dependencies are satisfied
   - Build order is preserved

2. **Production Deployment**:
   - Services start briefly then exit with success
   - No resources consumed (containers stop immediately)
   - All dependency validations pass
   - No special flags or profiles needed

3. **Simplicity**:
   - Single docker-compose.yml works everywhere
   - No conditional logic based on environment
   - No need to remember special commands

### Behavior

- `docker compose build` - Builds the images as normal
- `docker compose up -d` - Services start, exit immediately, stay stopped
- `docker compose pull` - Tries to pull (fails) but doesn't block other services

### Trade-offs

**Pros**:
- Simple, works everywhere
- No environment-specific configuration
- Clear intent (services that do nothing)

**Cons**:
- Services appear in `docker ps -a` as exited containers
- Slight startup overhead (containers start then stop)
- Not "pure" - mixing build and runtime concerns

## Alternative Approaches

If we wanted a "cleaner" solution in the future:
1. Move to separate build and runtime compose files
2. Use a build orchestration tool (e.g., BuildKit, Earthly)
3. Remove build concerns from docker-compose entirely

For now, the exit-on-start approach provides the best balance of simplicity and functionality.