# Batch Submission Patterns with React Query

## Current Implementation Issues

The current batch submission uses a simple for loop that has several problems:

1. **No rate limiting** - Fires all requests immediately, causing 429 errors
2. **No backoff strategy** - Doesn't respect server rate limits
3. **Sequential execution** - Slow for large batches
4. **No retry logic** - Network errors fail permanently
5. **Poor progress feedback** - User waits with no visibility

## Better Patterns with React Query

### 1. Sequential with Delays

Simple but effective for small batches:

```typescript
const submitMutation = useMutation({
  mutationFn: async (evaluation: EvaluationRequest) => {
    const response = await fetch(`${appConfig.api.baseUrl}/api/eval`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(evaluation),
    })
    if (!response.ok) throw new Error(`Failed: ${response.status}`)
    return response.json()
  },
  retry: 3,
  retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
})

// Submit with delays
for (const evaluation of evaluations) {
  try {
    const result = await submitMutation.mutateAsync(evaluation)
    results.push(result)
  } catch (error) {
    results.push({ error: error.message })
  }
  
  // Delay between submissions
  await new Promise(resolve => setTimeout(resolve, 200))
}
```

### 2. Batched Parallel Execution

Process in batches for better performance:

```typescript
const BATCH_SIZE = 5
const BATCH_DELAY = 500

for (let i = 0; i < evaluations.length; i += BATCH_SIZE) {
  const batch = evaluations.slice(i, i + BATCH_SIZE)
  
  // Submit batch in parallel
  const batchPromises = batch.map(eval => 
    submitMutation.mutateAsync(eval)
      .catch(error => ({ error: error.message }))
  )
  
  const batchResults = await Promise.all(batchPromises)
  results.push(...batchResults)
  
  // Delay between batches
  if (i + BATCH_SIZE < evaluations.length) {
    await new Promise(resolve => setTimeout(resolve, BATCH_DELAY))
  }
}
```

### 3. Controlled Concurrency with Rate Limiting

Most sophisticated approach using a concurrency limiter:

```typescript
import pLimit from 'p-limit'

// Limit to 3 concurrent requests
const limit = pLimit(3)

// Create staggered delays
const tasks = evaluations.map((eval, index) => 
  limit(async () => {
    // Stagger start times
    await new Promise(resolve => setTimeout(resolve, index * 100))
    
    try {
      return await submitMutation.mutateAsync(eval)
    } catch (error) {
      return { error: error.message }
    }
  })
)

const results = await Promise.all(tasks)
```

### 4. With Progress Feedback

Provide real-time feedback to users:

```typescript
const [progress, setProgress] = useState(0)

const submitBatch = async (evaluations: EvaluationRequest[]) => {
  const results = []
  
  for (let i = 0; i < evaluations.length; i++) {
    try {
      const result = await submitMutation.mutateAsync(evaluations[i])
      results.push(result)
    } catch (error) {
      results.push({ error: error.message })
    }
    
    // Update progress
    setProgress((i + 1) / evaluations.length * 100)
    
    // Rate limiting delay
    if (i < evaluations.length - 1) {
      await new Promise(resolve => setTimeout(resolve, 150))
    }
  }
  
  return results
}
```

## Why React Query Over Custom Logic?

1. **Built-in Retry Logic** - Exponential backoff out of the box
2. **Request Deduplication** - Prevents duplicate requests automatically
3. **Error Boundaries** - Integrates with React error handling
4. **Loading States** - `isLoading`, `isError` available immediately
5. **Cache Management** - Automatic cache invalidation and updates
6. **DevTools** - Inspect all queries/mutations in browser
7. **Optimistic Updates** - Update UI before server confirms

## Recommendations

- **Small batches (< 10)**: Use sequential with delays
- **Medium batches (10-50)**: Use batched parallel execution
- **Large batches (50+)**: Use controlled concurrency or consider a proper job queue
- **User-facing**: Always add progress feedback
- **Critical operations**: Add retry logic and error recovery

## Future Improvements

1. **Server-side batch endpoint** - Submit all at once, let server handle queuing
2. **WebSocket progress** - Real-time updates instead of polling
3. **Background job processing** - Move large batches to background workers
4. **Rate limit headers** - Read `X-RateLimit-*` headers to adjust dynamically