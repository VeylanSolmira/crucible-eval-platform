# Async Evaluation Pattern

## Decision: Deprecate Synchronous `/eval` Endpoint

### The Problem

Synchronous code execution endpoints are an anti-pattern for several reasons:

1. **Timeout Issues**
   - Code execution can take 30+ seconds (our current limit)
   - HTTP clients timeout at 30-60 seconds typically
   - Load balancers/API gateways timeout even sooner
   - Results in poor user experience

2. **Resource Blocking**
   - Each sync request ties up a server thread/worker
   - Can't handle concurrent evaluations efficiently
   - One slow evaluation can block others

3. **No Progress Updates**
   - Client just waits with no feedback
   - Can't show progress or intermediate results
   - Looks like the system is frozen

4. **Production Anti-Pattern**
   - Real systems use async for any operation > 1 second
   - Industry standard: Submit → Poll → Retrieve

### The Solution: Async-First API

```
POST /eval-async
→ Returns immediately with eval_id
→ Client polls /eval-status/{eval_id}
→ Or uses WebSocket for real-time updates
```

### Implementation

1. **Deprecation (Current)**
   ```http
   POST /eval
   → 410 Gone
   → Returns deprecation notice with alternative
   ```

2. **Async Flow**
   ```http
   POST /eval-async
   → 202 Accepted
   → {"eval_id": "abc123", "status": "queued"}
   
   GET /eval-status/abc123
   → {"status": "running", "progress": 50}
   → {"status": "completed", "output": "..."}
   ```

### Benefits

- **Scalable**: Can queue thousands of evaluations
- **Responsive**: UI never freezes
- **Informative**: Can show progress/status
- **Reliable**: No timeout issues
- **Standard**: Follows REST best practices

### Migration Guide

**Before (Synchronous):**
```javascript
const result = await fetch('/api/eval', {
  method: 'POST',
  body: JSON.stringify({code})
});
// Might timeout!
```

**After (Asynchronous):**
```javascript
// Submit evaluation
const submission = await fetch('/api/eval-async', {
  method: 'POST',
  body: JSON.stringify({code})
});
const {eval_id} = await submission.json();

// Poll for results
let result;
do {
  await sleep(1000);
  const status = await fetch(`/api/eval-status/${eval_id}`);
  result = await status.json();
} while (result.status === 'running');
```

### Future Enhancements

1. **WebSocket Support**
   - Real-time status updates
   - No polling needed
   - Better for UI responsiveness

2. **Batch Operations**
   - Submit multiple evaluations
   - Track collective progress
   - Efficient for testing suites

3. **Webhooks**
   - POST results to callback URL
   - Good for automation/CI
   - No polling required

### Conclusion

Removing synchronous evaluation endpoints is a necessary step toward a production-ready platform. The async pattern provides better scalability, reliability, and user experience.