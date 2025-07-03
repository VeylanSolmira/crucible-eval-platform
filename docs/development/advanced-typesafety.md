# Advanced TypeScript Type Safety

This document covers advanced TypeScript patterns and techniques for achieving maximum type safety in the codebase.

## Removing `unknown` Types

The `unknown` type is safer than `any` but still represents a loss of type information. Here are strategies for eliminating `unknown` types while maintaining type safety.

### Case Study: SmartApiClient Queue Implementation

The `smartApiClient.ts` currently uses `unknown` in its queue implementation:

```typescript
interface QueuedRequest {
  execute: () => Promise<Response>
  resolve: (value: unknown) => void
  reject: (error: unknown) => void
  retries: number
}
```

#### Option 1: Maintain Type Through Queue (Complex)

To fully preserve types through the queue, we would need to make the queue itself generic:

```typescript
interface QueuedRequest<T> {
  execute: () => Promise<Response>
  resolve: (value: T) => void
  reject: (error: unknown) => void
  retries: number
}

class SmartApiClient {
  // Problem: Can't have a single queue for different types
  private queue: QueuedRequest<any>[] = [] // Still loses type safety
  
  // Would need separate queues per type or complex type tracking
}
```

This approach has significant drawbacks:
- Requires complex type gymnastics to handle heterogeneous requests
- May need runtime type information storage
- Increases code complexity substantially

#### Option 2: Discriminated Unions (Moderate)

Use discriminated unions to handle known request types:

```typescript
type KnownApiResponse = 
  | { type: 'evaluation'; data: EvaluationResult }
  | { type: 'batch'; data: BatchSubmissionResult[] }
  | { type: 'status'; data: EvaluationStatus }

interface QueuedRequest {
  execute: () => Promise<Response>
  resolve: (value: KnownApiResponse) => void
  reject: (error: unknown) => void
  retries: number
  responseType: KnownApiResponse['type']
}
```

Benefits:
- Type-safe for known response types
- Can validate at runtime based on `responseType`
- Extensible for new response types

Drawbacks:
- Requires maintaining union type
- Generic endpoints still need fallback

#### Option 3: Pragmatic Approach (Current)

Keep `unknown` but ensure type safety at the API boundaries:

```typescript
async fetch<T>(url: string, options?: RequestInit): Promise<T> {
  return new Promise((resolve, reject) => {
    const request: QueuedRequest = {
      execute: () => fetch(`${this.baseUrl}${url}`, options),
      resolve, // Type erasure happens here
      reject,
      retries: 0,
    }
    // ...
  })
}

// Type safety restored at usage:
const result = await smartApi.fetch<EvaluationResult>('/api/eval/123')
// result is typed as EvaluationResult
```

Benefits:
- Simple implementation
- Type safety at API boundaries
- No runtime overhead
- Works with any response type

Drawbacks:
- Internal queue operations use `unknown`
- Relies on caller to specify correct type

### Best Practices for Type Safety

1. **Use `unknown` over `any`**: When type information is genuinely unknown, `unknown` forces explicit type checking.

2. **Type at boundaries**: Ensure strong typing at API boundaries even if internals use `unknown`.

3. **Runtime validation**: When receiving external data, validate and narrow types:
   ```typescript
   function isEvaluationResult(data: unknown): data is EvaluationResult {
     return (
       typeof data === 'object' &&
       data !== null &&
       'eval_id' in data &&
       'status' in data
     )
   }
   ```

4. **Generic constraints**: Use generic constraints to limit type parameters:
   ```typescript
   function processApiResponse<T extends { id: string }>(response: T): T {
     console.log(`Processing response ${response.id}`)
     return response
   }
   ```

5. **Template literal types**: Use for string manipulation with type safety:
   ```typescript
   type ApiEndpoint = `/api/${string}`
   function callApi(endpoint: ApiEndpoint) { /* ... */ }
   ```

## Strict Compiler Options

Enable these TypeScript compiler options for maximum type safety:

```json
{
  "compilerOptions": {
    "strict": true,                          // Enable all strict type checking options
    "noImplicitAny": true,                  // Error on expressions with 'any' type
    "strictNullChecks": true,               // Enable strict null checks
    "strictFunctionTypes": true,            // Enable strict checking of function types
    "strictBindCallApply": true,            // Enable strict 'bind', 'call', and 'apply'
    "strictPropertyInitialization": true,   // Ensure properties are initialized
    "noImplicitThis": true,                 // Error on 'this' with 'any' type
    "useUnknownInCatchVariables": true,     // Default catch variables to 'unknown'
    "alwaysStrict": true,                   // Ensure 'use strict' in all files
    "exactOptionalPropertyTypes": true,     // Differentiate between undefined and optional
    "noUncheckedIndexedAccess": true,       // Add undefined to index signatures
    "noImplicitOverride": true,             // Ensure 'override' keyword is used
    "noPropertyAccessFromIndexSignature": true // Require indexed access for index signatures
  }
}
```

## Advanced Type Patterns

### Branded Types
Prevent mixing of similar primitive types:

```typescript
type UserId = string & { __brand: 'UserId' }
type PostId = string & { __brand: 'PostId' }

function getUser(id: UserId) { /* ... */ }
function getPost(id: PostId) { /* ... */ }

const userId = '123' as UserId
const postId = '456' as PostId

getUser(userId) // ✓ OK
getUser(postId) // ✗ Type error
```

### Const Assertions
Use `as const` for literal types:

```typescript
const config = {
  api: '/api/v1',
  timeout: 5000,
  retries: 3
} as const

// Type is: { readonly api: "/api/v1"; readonly timeout: 5000; readonly retries: 3 }
```

### Type Predicates
Create custom type guards:

```typescript
function isNonNullable<T>(value: T): value is NonNullable<T> {
  return value !== null && value !== undefined
}

const values: (string | null)[] = ['a', null, 'b']
const filtered = values.filter(isNonNullable) // Type: string[]
```

### Exhaustive Checks
Ensure all cases are handled:

```typescript
type Status = 'pending' | 'success' | 'error'

function handleStatus(status: Status) {
  switch (status) {
    case 'pending': return 'Loading...'
    case 'success': return 'Done!'
    case 'error': return 'Failed!'
    default:
      const exhaustive: never = status
      throw new Error(`Unhandled status: ${exhaustive}`)
  }
}
```

## Is Zero `unknown` Types Desirable in Production?

No, eliminating all `unknown` types is not desirable even at the highest levels of production coding. Here's why:

### When `unknown` is Actually Correct

1. **External Data Boundaries**: When receiving data from APIs, user input, or file systems, the type genuinely IS unknown until validated. Using `unknown` forces proper validation.

2. **Error Handling**: Catch blocks should use `unknown` because JavaScript can throw literally anything:
   ```typescript
   try {
     // ...
   } catch (error: unknown) {
     // Must validate before using error
   }
   ```

3. **Generic Event Systems**: Event emitters, message queues, or plugin systems often handle truly dynamic data.

4. **Serialization Boundaries**: JSON.parse returns `unknown` - this is correct because JSON can contain anything.

### The Cost of Eliminating `unknown`

Trying to eliminate all `unknown` types often leads to:
- **Over-engineering**: Complex type gymnastics that obscure intent
- **False confidence**: Lying with `as` casts or incorrect type definitions
- **Maintenance burden**: Types that need constant updates as data shapes evolve
- **Runtime overhead**: Additional code to maintain type information

### What Top Codebases Actually Do

Looking at codebases like TypeScript compiler, VSCode, or React:
- They use `unknown` at boundaries
- They validate and narrow types immediately
- They don't try to preserve types through every layer

### The Better Goal

Instead of "no unknowns", aim for:
1. **Minimize scope**: Use `unknown` only at true boundaries
2. **Validate immediately**: Convert to known types ASAP
3. **Type guards**: Make validation reusable
4. **Document why**: When you use `unknown`, explain why

```typescript
// Good: Unknown at boundary, validated immediately
async function fetchUser(id: string): Promise<User> {
  const response = await fetch(`/api/users/${id}`)
  const data: unknown = await response.json()
  
  if (!isUser(data)) {
    throw new Error('Invalid user data')
  }
  
  return data // Now typed as User
}
```

The mark of high-level production code isn't the absence of `unknown` - it's using `unknown` correctly to model genuine uncertainty while maintaining type safety everywhere else.

## Conclusion

While removing all `unknown` types is theoretically possible, it's not always practical or beneficial. The key is to:

1. Use `unknown` judiciously where type information is genuinely dynamic
2. Ensure type safety at API boundaries
3. Validate and narrow types when working with external data
4. Use TypeScript's strict options to catch potential issues
5. Apply advanced patterns where they provide clear benefits

The goal is pragmatic type safety that helps prevent bugs without overcomplicating the codebase.