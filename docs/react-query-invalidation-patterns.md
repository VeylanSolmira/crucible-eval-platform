# React Query Cache Invalidation Patterns

## Problem

When using polling with React Query, naive cache invalidation can cause request storms when multiple evaluations complete simultaneously. Each completion triggers a global invalidation, causing all queries to refetch.

## Current Issue

```typescript
// Too broad - invalidates ALL evaluation queries
queryClient.invalidateQueries({ queryKey: ['evaluations'] })
```

This causes 429 (Too Many Requests) errors when many evaluations are running.

## Better Patterns

### 1. Tag by Evaluation IDs

Include evaluation IDs in the query key and only invalidate if affected:

```typescript
// When fetching running list, include eval IDs in the key
queryKey: ['evaluations', 'running', { evalIds: runningEvalIds }]

// When eval completes, only invalidate if that ID is in the list
queryClient.invalidateQueries({ 
  queryKey: ['evaluations', 'running'],
  predicate: (query) => {
    const evalIds = query.queryKey[2]?.evalIds || []
    return evalIds.includes(completedEvalId)
  }
})
```

### 2. Hierarchical Keys with Partial Matching

Structure query keys hierarchically and use exact: false:

```typescript
// Tag specific evaluation queries
queryKey: ['evaluation', evalId, 'status']
queryKey: ['evaluation', evalId, 'logs']
queryKey: ['evaluation', evalId, 'details']

// Invalidate all queries for that specific evaluation
queryClient.invalidateQueries({ 
  queryKey: ['evaluation', evalId],
  exact: false  // Matches all subkeys
})
```

### 3. Smart Predicate Functions

Only invalidate caches that actually contain the affected data:

```typescript
// Only invalidate if the cached data contains the completed evaluation
queryClient.invalidateQueries({
  predicate: (query) => {
    if (query.queryKey[0] === 'evaluations' && query.queryKey[1] === 'running') {
      const data = query.state.data
      return data?.evaluations?.some(e => e.eval_id === completedEvalId)
    }
    return false
  }
})
```

### 4. Debounced Invalidation

Batch multiple invalidations together:

```typescript
const debouncedInvalidate = debounce(() => {
  queryClient.invalidateQueries({ queryKey: ['evaluations', 'running'] })
}, 500)

// When evaluations complete, call debounced version
debouncedInvalidate()
```

## Trade-offs

- **More complex code** - Requires careful key design and predicate logic
- **Potential for stale data** - If invalidation is too narrow, might miss updates
- **Performance vs correctness** - More targeted = better performance but higher chance of bugs

## Long-term Solution

These patterns are workarounds for the fundamental limitations of polling. Consider:

1. **WebSockets** - Real-time updates without polling
2. **Server-Sent Events (SSE)** - One-way real-time updates
3. **Subscription model** - Subscribe to specific evaluation updates

These would eliminate the need for polling and complex cache invalidation entirely.