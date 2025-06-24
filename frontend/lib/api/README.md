# OpenAPI to TypeScript Code Generation

This directory contains the type-safe API client for the Crucible Evaluation Platform. The types are automatically generated from the OpenAPI specification to ensure compile-time safety and catch API contract mismatches.

## Setup

### 1. Generate Types

Before using the API client, you need to generate the TypeScript types from the OpenAPI spec:

```bash
# Make sure the API server is running on localhost:8080
npm run generate-types

# Or if using Docker
npm run generate-types:docker
```

This will create `/types/generated/api.ts` with all the type definitions from the OpenAPI spec.

### 2. Build-time Type Checking

The build process automatically generates types to catch API contract mismatches:

```bash
npm run build  # This runs generate-types before building

# To skip type generation (if API is not available)
npm run build:skip-types
```

## Usage

### Basic API Client

```typescript
import { apiClient } from '@/lib/api/client'
import type { EvaluationRequest } from '@/lib/api/client'

// Submit an evaluation
const request: EvaluationRequest = {
  code: 'print("Hello, World!")',
  timeout: 30,
  resources: {
    memory_mb: 512,
    cpu_shares: 1024
  }
}

const { data, error } = await apiClient.submitEvaluation(request)
```

### React Hooks

```typescript
import { useEvaluation, useEvaluationStatus } from '@/lib/api/hooks'

function MyComponent() {
  const { submitEvaluation, isSubmitting, error } = useEvaluation()
  const { status, isLoading } = useEvaluationStatus(evalId)
  
  // Use the hooks in your component
}
```

## Type Safety Benefits

1. **Compile-time checking**: TypeScript will catch any mismatches between your code and the API contract
2. **Auto-completion**: Your IDE will provide intelligent suggestions based on the API schema
3. **Refactoring safety**: Changes to the API will be caught during the build process
4. **Documentation**: The generated types serve as living documentation of the API

## Troubleshooting

### Types not generating

1. Ensure the API server is running at `http://localhost:8080`
2. Check that the OpenAPI endpoint is accessible: `curl http://localhost:8080/api/openapi.json`
3. Look for errors in the console when running `npm run generate-types`

### Type mismatches

If you see TypeScript errors after generating types:

1. The API contract may have changed - regenerate types with `npm run generate-types`
2. Check if you're using the correct version of the API
3. Ensure all team members have regenerated types after API changes

## Development Workflow

1. Start the API server
2. Run `npm run generate-types` to update types
3. Use the typed API client in your components
4. TypeScript will catch any contract violations at compile time
5. The build process will fail if types don't match, preventing deployment of incompatible code