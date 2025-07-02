# Crucible Platform Frontend

Next.js frontend for the Crucible Evaluation Platform.

## Development Setup

### Prerequisites

- Node.js 20+
- Backend API running on http://localhost:8080

### Install Dependencies

```bash
npm install
```

### Generate TypeScript Types from API

```bash
# Ensure backend is running first!
docker-compose up -d api-service

# Generate types from OpenAPI spec
npm run generate-types
```

### Development Server

```bash
npm run dev
# Visit http://localhost:3000
```

## Type Safety with OpenAPI

This project uses auto-generated TypeScript types from the backend's OpenAPI specification.

### When to Generate Types

- After any backend API changes
- Before committing frontend changes
- When pulling new code

### Type Generation Commands

```bash
# For local development (requires API at localhost:8080)
npm run generate-types

# For Docker environments (requires API at crucible-platform:8080)
npm run generate-types:docker
```

### Build Commands

```bash
# Standard build (uses existing types)
npm run build

# Local build with fresh types (requires running API)
npm run build:local
```

## Docker Build

The Dockerfile uses committed types for faster, more reliable builds:

```bash
# Build the image
docker build -t crucible-frontend .

# Or via docker-compose
docker-compose build crucible-frontend
```

## Type Safety Workflow

1. **Backend changes API** → OpenAPI spec updates automatically
2. **Frontend developer** runs `npm run generate-types`
3. **TypeScript** shows errors if frontend doesn't match new API
4. **Fix code** to match new types
5. **Commit both** code changes and generated types
6. **Docker build** uses committed types for type checking

## Best Practices

### DO:

- ✅ Run `npm run generate-types` after pulling new code
- ✅ Commit generated types to git
- ✅ Use the typed API client for all API calls
- ✅ Let TypeScript catch API mismatches

### DON'T:

- ❌ Manually edit files in `types/generated/`
- ❌ Ignore TypeScript errors about API types
- ❌ Use `any` to bypass type checking
- ❌ Make API calls without the typed client

## Troubleshooting

### "Cannot find module '@/types/generated/api'"

Run `npm run generate-types` to generate the types file.

### "Property 'X' does not exist on type 'Y'"

The API changed. Run `npm run generate-types` and update your code.

### Build fails with type errors

1. Ensure you have the latest types: `npm run generate-types`
2. Fix any TypeScript errors
3. If types are correct but build still fails, check for version mismatches

## Architecture Decisions

### Why commit generated types?

1. **Reliable Docker builds** - No external dependencies
2. **Git history** - See API changes in PRs
3. **Offline development** - Can work without backend running
4. **CI/CD simplicity** - Builds don't need running services

### Why TypeScript + OpenAPI?

1. **Catch errors early** - At compile time, not runtime
2. **Better DX** - Auto-completion and inline docs
3. **Refactor safely** - TypeScript guides the changes
4. **Living documentation** - Types always match API
