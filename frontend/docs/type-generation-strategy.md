# Type Generation Strategy

## The Goal
Ensure frontend TypeScript code matches the backend API contract, catching mismatches at build time.

## The Challenge
- We want fresh types from the API during build
- But Docker builds are isolated - no access to other services
- Local `npm run build` CAN access localhost:8080
- Docker `npm run build` CANNOT access the API

## Strategies

### Option 1: Different Commands for Different Contexts

**package.json:**
```json
{
  "scripts": {
    "build": "next build",                    // For Docker (no type gen)
    "build:local": "npm run generate-types && next build",  // For local dev
    "build:ci": "npm run generate-types && next build"      // For CI with API running
  }
}
```

**Local development:**
```bash
npm run build:local  # Generates types + builds
```

**Dockerfile:**
```dockerfile
RUN npm run build  # Just builds with existing types
```

**CI/CD:**
```yaml
- name: Start API
  run: docker-compose up -d api-service
- name: Build with fresh types  
  run: npm run build:ci
```

### Option 2: Pre-build Type Generation

**Makefile approach:**
```makefile
build-frontend:
	docker-compose up -d api-service
	npm run generate-types
	docker build -t frontend .
```

### Option 3: Build-time Type Checking Only

Keep types in git but verify they're current:

**package.json:**
```json
{
  "scripts": {
    "type-check": "tsc --noEmit",
    "type-check:fresh": "npm run generate-types && npm run type-check",
    "build": "npm run type-check && next build"
  }
}
```

### Option 4: Multi-stage Docker Build with Docker-in-Docker

Complex but fully self-contained:
```dockerfile
# Stage 1: Generate types
FROM docker:dind AS types
# ... start API container, generate types ...

# Stage 2: Build
FROM node:20 AS build
COPY --from=types /types ./types
RUN npm run build
```

## Recommended Approach

**For this project: Option 1** - Different commands for different contexts

Why:
1. **Simple** - Easy to understand and maintain
2. **Flexible** - Each environment does what makes sense
3. **Fast** - Docker builds don't need to start services
4. **Safe** - CI can still verify types match

**Implementation:**
- Developers run `npm run generate-types` when API changes
- Commit generated types
- Docker uses committed types
- CI regenerates types to verify they match
- If CI fails, we know types are out of sync