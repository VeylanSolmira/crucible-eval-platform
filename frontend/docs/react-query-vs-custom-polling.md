# React Query vs Custom Polling: A Case Study

## The Problem

Supporting batch evaluations with individual status tracking - a common pattern in evaluation platforms where you need to:

1. Submit multiple evaluations at once
2. Track each evaluation's progress independently
3. Update the UI as each completes
4. Handle failures gracefully

## Original Custom Solution (~100 lines)

```javascript
// smartApi handled rate limiting, retries, and batch submissions
const results = await smartApi.submitBatch(evaluations)

// One function managed all polling
pollBatchEvaluationStatus(evalId, resultsMap)

// Single Map tracked everything
setMultipleResults(new Map(resultsMap))
```

**Pros:**

- Purpose-built for this exact use case
- Clean separation of concerns
- Built-in rate limiting and retry logic
- Single source of truth (Map)

## React Query Solution (200+ lines and growing)

```javascript
// Multiple hooks needed
useBatchSubmit()
useMultipleEvaluations(evalIds)
useQueueStatus()

// Multiple state variables
const [batchResults, setBatchResults] = useState([])
const [batchEvalIds, setBatchEvalIds] = useState([])
const { data: batchEvaluations } = useMultipleEvaluations(batchEvalIds)

// Complex merging of initial results with polling data
const currentEval = batchEvaluations?.find(e => e.eval_id === result.eval_id)
const status = currentEval?.status || (result.error ? 'error' : 'submitted')
```

**Cons:**

- More code than the original
- Complex state synchronization
- Lost features (rate limiting, smart retries)
- Fighting the library's design

## The Mismatch

React Query excels at simple patterns:

- Fetch data → display it
- Submit form → show result

But our use case is more complex:

- Submit 5 evaluations → get 5 IDs → poll 5 statuses independently → merge results → display updates

This mismatch means we're essentially rebuilding custom polling logic but spread across multiple hooks and components.

## The Lesson

Sometimes a well-designed custom solution that fits your exact needs is better than forcing a general-purpose library to handle a complex use case. The original code was actually quite elegant for this specific problem.

**However**, as noted in the conversation:

- Batch submissions are essential in evaluation contexts
- Mixing React Query and custom solutions adds cognitive overhead
- Since we're already committed to React Query for single evaluations, it's probably best to complete the implementation

The key insight: Not every "modern" solution is simpler. Choose tools that match your use case, not just what's popular.
