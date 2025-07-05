# Batch Endpoints Design Guide

## Overview

Batch endpoints are a common pattern in REST APIs that allow clients to perform multiple operations in a single HTTP request. This document covers design patterns, implementation strategies, and rate limiting approaches.

## Why Batch Endpoints?

### Benefits
1. **Performance** - Reduces HTTP overhead (headers, connection establishment)
2. **Atomicity** - Can implement transactional semantics
3. **Rate Limiting** - Easier to control on server side
4. **Progress Tracking** - Can return job IDs for async processing
5. **Error Handling** - Standardized partial success patterns
6. **Network Efficiency** - Fewer round trips, especially important for mobile clients

### Trade-offs
1. **Complexity** - More complex error handling
2. **Timeout Risk** - Large batches may hit HTTP timeouts
3. **Memory Usage** - Server must handle larger payloads
4. **Debugging** - Harder to trace individual operations

## Common Batch Endpoint Patterns

### 1. Synchronous Batch Processing
```python
POST /api/users/batch
{
  "users": [
    {"name": "Alice", "email": "alice@example.com"},
    {"name": "Bob", "email": "bob@example.com"}
  ]
}

Response:
{
  "succeeded": 2,
  "failed": 0,
  "results": [
    {"index": 0, "id": "123", "status": "created"},
    {"index": 1, "id": "124", "status": "created"}
  ]
}
```

**Use when**: Operations are fast and results are needed immediately.

### 2. Asynchronous Batch with Job ID
```python
POST /api/reports/batch
{
  "reports": [...]
}

Response:
{
  "job_id": "batch-12345",
  "status": "accepted",
  "check_url": "/api/jobs/batch-12345",
  "estimated_completion": "2024-01-01T12:00:00Z"
}

# Client polls for status
GET /api/jobs/batch-12345
{
  "status": "processing",
  "progress": 45,
  "completed": 45,
  "total": 100
}
```

**Use when**: Operations are slow or resource-intensive.

### 3. Transactional Batch (All or Nothing)
```python
POST /api/transactions/batch
{
  "atomic": true,  # All succeed or all fail
  "transactions": [
    {"from": "A", "to": "B", "amount": 100},
    {"from": "B", "to": "C", "amount": 50}
  ]
}

Response (Success):
{
  "status": "committed",
  "transaction_id": "tx-789",
  "results": [...]
}

Response (Failure):
{
  "status": "rolled_back",
  "error": "Insufficient funds in account B",
  "failed_at_index": 1
}
```

**Use when**: Operations must maintain consistency.

### 4. Streaming Results (JSONL/Server-Sent Events)
```python
POST /api/validations/batch
Accept: application/x-ndjson

Response (JSONL):
{"index": 0, "result": "success", "id": "123"}
{"index": 1, "result": "failed", "error": "Invalid format"}
{"index": 2, "result": "success", "id": "125"}
```

**Use when**: Real-time feedback is important.

### 5. Hybrid Sync/Async
```python
POST /api/eval-batch
{
  "evaluations": [...],
  "mode": "async"  # or "sync" for small batches
}

Response (Async):
{
  "job_id": "batch-123",
  "evaluations": [
    {"eval_id": "eval_1", "status": "queued"},
    {"eval_id": "eval_2", "status": "queued"}
  ]
}
```

**Use when**: You want flexibility based on batch size.

## Rate Limiting Strategies

### Python Implementation Options

#### 1. asyncio-throttle (Pure Async)
```python
from asyncio_throttle import Throttler

# 10 requests per second
throttler = Throttler(rate_limit=10, period=1.0)

async def process_batch(items):
    async with throttler:
        for item in items:
            async with throttler:
                await process_item(item)
```

**Pros**: Simple, async-native
**Cons**: Extra dependency

#### 2. slowapi (FastAPI-specific)
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/batch")
@limiter.limit("100/minute")
async def batch_endpoint(request: BatchRequest):
    # Endpoint-level rate limiting
    pass
```

**Pros**: Integrates with FastAPI, supports Redis backend
**Cons**: Only for endpoint-level limiting

#### 3. Simple asyncio.sleep (Most Common)
```python
import asyncio

async def process_with_rate_limit(items, rate_limit=10):
    """Process items with rate limiting (items per second)"""
    delay = 1.0 / rate_limit
    
    for item in items:
        await process_item(item)
        await asyncio.sleep(delay)
```

**Pros**: No dependencies, simple to understand
**Cons**: Basic, no burst handling

#### 4. Token Bucket Algorithm
```python
import asyncio
import time

class TokenBucket:
    def __init__(self, capacity, refill_rate):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def consume(self, tokens=1):
        async with self.lock:
            await self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            # Calculate wait time
            needed = tokens - self.tokens
            wait_time = needed / self.refill_rate
            await asyncio.sleep(wait_time)
            
            await self._refill()
            self.tokens -= tokens
            return True
    
    async def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

# Usage: Allow bursts of 20, refill at 10/second
bucket = TokenBucket(capacity=20, refill_rate=10)

async def process_batch(items):
    for item in items:
        await bucket.consume(1)
        await process_item(item)
```

**Pros**: Handles bursts, more sophisticated
**Cons**: More complex

#### 5. Semaphore-based Limiting
```python
import asyncio

class RateLimiter:
    def __init__(self, rate, per):
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = asyncio.get_event_loop().time()
    
    async def acquire(self):
        current = asyncio.get_event_loop().time()
        time_passed = current - self.last_check
        self.last_check = current
        self.allowance += time_passed * (self.rate / self.per)
        
        if self.allowance > self.rate:
            self.allowance = self.rate
        
        if self.allowance < 1.0:
            sleep_time = (1.0 - self.allowance) * (self.per / self.rate)
            await asyncio.sleep(sleep_time)
            self.allowance = 0.0
        else:
            self.allowance -= 1.0
```

**Pros**: Smooth rate limiting
**Cons**: More complex than needed for most cases

## Best Practices

### 1. Batch Size Limits
```python
MAX_BATCH_SIZE = 100

@app.post("/api/batch")
async def batch_endpoint(request: BatchRequest):
    if len(request.items) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size exceeds maximum of {MAX_BATCH_SIZE}"
        )
```

### 2. Timeout Handling
```python
@app.post("/api/batch")
async def batch_endpoint(request: BatchRequest):
    try:
        async with asyncio.timeout(30):  # 30 second timeout
            return await process_batch(request)
    except asyncio.TimeoutError:
        return {
            "status": "partial",
            "message": "Batch processing timed out",
            "processed": processed_count
        }
```

### 3. Progress Reporting
```python
async def process_batch_with_progress(batch_id, items):
    total = len(items)
    
    for i, item in enumerate(items):
        await process_item(item)
        
        # Update progress in cache/database
        await redis.set(
            f"batch:{batch_id}:progress",
            json.dumps({"processed": i + 1, "total": total}),
            ex=3600
        )
```

### 4. Error Collection
```python
@app.post("/api/batch")
async def batch_endpoint(request: BatchRequest):
    results = []
    errors = []
    
    for i, item in enumerate(request.items):
        try:
            result = await process_item(item)
            results.append({"index": i, "status": "success", "data": result})
        except Exception as e:
            errors.append({"index": i, "status": "error", "error": str(e)})
            results.append({"index": i, "status": "error"})
    
    return {
        "total": len(request.items),
        "succeeded": len(request.items) - len(errors),
        "failed": len(errors),
        "results": results,
        "errors": errors if errors else None
    }
```

### 5. Idempotency
```python
@app.post("/api/batch")
async def batch_endpoint(
    request: BatchRequest,
    idempotency_key: str = Header(None, alias="Idempotency-Key")
):
    if idempotency_key:
        # Check if we've seen this key before
        cached = await redis.get(f"idempotency:{idempotency_key}")
        if cached:
            return json.loads(cached)
    
    result = await process_batch(request)
    
    if idempotency_key:
        # Cache result for 24 hours
        await redis.set(
            f"idempotency:{idempotency_key}",
            json.dumps(result),
            ex=86400
        )
    
    return result
```

## Implementation Recommendations

### For Evaluation Platform

Given the evaluation platform's requirements:
- Evaluations are independent (no transactional needs)
- Processing is async via Celery
- Need to prevent overwhelming downstream services
- Want immediate feedback (eval_ids)

**Recommended approach**:

```python
@app.post("/api/eval-batch")
async def evaluate_batch(request: BatchEvaluationRequest):
    # Validate batch size
    if len(request.evaluations) > 100:
        raise HTTPException(400, "Maximum batch size is 100")
    
    results = []
    
    # Process in sub-batches with rate limiting
    BATCH_SIZE = 5
    DELAY_BETWEEN_ITEMS = 0.1  # 10 items/second
    DELAY_BETWEEN_BATCHES = 0.5
    
    for i in range(0, len(request.evaluations), BATCH_SIZE):
        batch = request.evaluations[i:i + BATCH_SIZE]
        
        # Process batch items
        for evaluation in batch:
            eval_id = generate_eval_id()
            
            # Submit to Celery (non-blocking)
            celery_task_id = submit_evaluation_to_celery(
                eval_id=eval_id,
                code=evaluation.code,
                language=evaluation.language,
                priority=evaluation.priority
            )
            
            results.append({
                "eval_id": eval_id,
                "status": "queued",
                "celery_task_id": celery_task_id
            })
            
            # Rate limit between items
            await asyncio.sleep(DELAY_BETWEEN_ITEMS)
        
        # Delay between batches
        if i + BATCH_SIZE < len(request.evaluations):
            await asyncio.sleep(DELAY_BETWEEN_BATCHES)
    
    return {
        "evaluations": results,
        "total": len(results),
        "queued": len(results)
    }
```

This provides:
- Simple rate limiting without dependencies
- Immediate response with all eval_ids
- Prevents overwhelming Celery/executors
- Easy to tune rates
- No "batch" concept in evaluation domain

## Common Pitfalls

1. **No Rate Limiting** - Overwhelming downstream services
2. **Blocking Operations** - Using sync operations in async handlers
3. **Memory Issues** - Loading entire batch into memory
4. **No Size Limits** - Accepting unlimited batch sizes
5. **Poor Error Handling** - Failing entire batch on single error
6. **No Progress Feedback** - Long running batches with no updates
7. **Missing Idempotency** - No protection against duplicate submissions

## Conclusion

Batch endpoints are a valuable pattern when:
- Network efficiency matters
- Operations can be optimized in bulk
- Clients need to submit multiple items

The key is to implement them as an optimization layer without leaking the "batch" concept into your domain model. Each item in the batch should remain independent and be processed according to the same business rules as individual submissions.