# OpenAPI + TypeScript Integration Primer

## What is OpenAPI?

OpenAPI (formerly Swagger) is a specification for describing REST APIs. It's like a contract that defines:

- What endpoints exist (`/api/eval`, `/api/status`, etc.)
- What data they expect (request body structure)
- What data they return (response structure)
- What errors might occur

## Why OpenAPI + TypeScript?

### The Problem

Without type safety between frontend and backend:

```typescript
// Frontend code - we're just guessing the structure!
const response = await fetch('/api/eval-status/123')
const data = await response.json()

// Will this work? Who knows! 🤷
console.log(data.result.output) // Maybe it's data.output?
console.log(data.eval_id) // Or is it data.id?
```

### The Solution

With OpenAPI + TypeScript:

```typescript
// TypeScript knows EXACTLY what the API returns
const { data } = await apiClient.getEvaluationStatus('123')
if (data) {
  console.log(data.output) // ✅ TypeScript knows this exists
  console.log(data.resultado) // ❌ TypeScript error: Property 'resultado' does not exist
}
```

## How It Works

### 1. Backend Exposes OpenAPI Spec

Your FastAPI backend automatically generates an OpenAPI specification:

- Available at: `http://localhost:8080/api/openapi.json`
- Describes every endpoint, request, and response

### 2. Frontend Generates TypeScript Types

```bash
npm run generate-types
```

This command:

1. Fetches the OpenAPI spec from your backend
2. Generates TypeScript interfaces matching your API exactly
3. Saves them to `/frontend/types/generated/api.d.ts`

### 3. Use Type-Safe Client

Instead of raw `fetch()`, use the typed client:

```typescript
import { apiClient } from '@/lib/api/client'

// TypeScript ensures you provide correct fields
const result = await apiClient.submitEvaluation({
  code: "print('hello')",
  language: 'python',
})
```

## The Development Flow

### Initial Setup (One Time)

1. Backend defines API endpoints
2. Frontend installs `openapi-typescript`
3. Configure type generation script

### Daily Development

1. **Backend Changes**: Developer modifies an API endpoint
2. **Generate Types**: Run `npm run generate-types`
3. **TypeScript Catches Issues**: Build fails if frontend doesn't match
4. **Fix and Ship**: Update frontend to match new API contract

## Real Example: The Bug We Just Fixed

### What Happened

1. API returns flat structure:

```json
{
  "eval_id": "123",
  "status": "completed",
  "output": "Hello, world!"
}
```

2. Frontend expected nested structure:

```typescript
// This was wrong!
const output = data.result.output
```

### How OpenAPI Would Have Caught This

With proper type generation:

```typescript
// TypeScript would show an error:
// Property 'result' does not exist on type 'EvaluationStatus'
const output = data.result.output // ❌ Compile error!

// TypeScript would suggest the correct path:
const output = data.output // ✅ This is correct!
```

## Benefits

1. **Catch Errors at Build Time**: No more runtime surprises
2. **Auto-completion**: Your IDE knows every field
3. **Refactoring Safety**: Change API? TypeScript shows you what to update
4. **Living Documentation**: Types serve as documentation
5. **Confidence**: If it compiles, it matches the API

## Common Patterns

### Making API Calls

```typescript
// Always handle both success and error
const { data, error } = await apiClient.submitEvaluation(request)

if (error) {
  console.error('API error:', error.message)
  return
}

// TypeScript knows data is defined here
console.log('Evaluation ID:', data.eval_id)
```

### Using in React Components

```typescript
function EvaluationStatus({ evalId }: { evalId: string }) {
  const [status, setStatus] = useState<EvaluationStatus | null>(null)

  useEffect(() => {
    async function checkStatus() {
      const { data, error } = await apiClient.getEvaluationStatus(evalId)
      if (data) setStatus(data)
    }
    checkStatus()
  }, [evalId])

  // TypeScript knows all available fields
  return <div>{status?.output}</div>
}
```

## Troubleshooting

### "Cannot find module '@/types/generated/api'"

- Run `npm run generate-types` first
- Make sure backend is running

### Types don't match reality

- Regenerate types: `npm run generate-types`
- Restart TypeScript server in VS Code: Cmd+Shift+P → "Restart TS Server"

### Build fails after API change

- This is good! It caught a mismatch
- Update your frontend code to match the new types

## Next Steps

1. Always run `npm run generate-types` after API changes
2. Use the typed client instead of raw fetch
3. Let TypeScript guide you - it knows the API structure
4. Commit generated types for CI/CD (or generate in CI)
