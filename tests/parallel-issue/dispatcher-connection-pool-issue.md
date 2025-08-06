# Dispatcher Connection Pool Exhaustion Issue

## Problem
The dispatcher service uses global singleton Kubernetes API clients that are shared across all concurrent requests. This causes issues during sustained parallel test execution.

## Current Implementation
```python
# Global clients - shared by all requests!
batch_v1 = client.BatchV1Api()
core_v1 = client.CoreV1Api()
node_v1 = client.NodeV1Api()
```

## Issues with This Approach

### 1. Connection Pool Exhaustion
- Default Kubernetes client has a limited connection pool (typically 10 connections)
- When parallel tests submit many evaluations concurrently, connections get exhausted
- Results in hanging requests or connection errors

### 2. Thread Safety
- The Kubernetes Python client may not be fully thread-safe
- Concurrent requests sharing the same client can cause race conditions
- May lead to corrupted requests or responses

### 3. No Rate Limiting
- No throttling of requests to Kubernetes API server
- Can overwhelm the API server during high load
- May trigger API server rate limiting, causing requests to fail

## Why This Affects Parallel Tests
- Integration tests: Submit ~25 evaluations
- E2E tests: Submit ~18 evaluations
- When running in parallel, both suites submit evaluations concurrently
- The shared client gets overwhelmed after sustained concurrent usage
- This explains why tests fail after running for a while, not immediately

## Solution Options

### Option 1: Per-Request Clients (Recommended)
Create new API clients for each request to avoid sharing:
```python
@app.post("/execute")
async def execute(request: ExecuteRequest):
    # Create fresh clients for this request
    batch_v1 = client.BatchV1Api()
    core_v1 = client.CoreV1Api()
    # ... rest of the function
```

### Option 2: Connection Pool Configuration
Configure the Kubernetes client with a larger connection pool:
```python
configuration = client.Configuration()
configuration.connection_pool_maxsize = 50  # Increase from default 10
api_client = client.ApiClient(configuration)
batch_v1 = client.BatchV1Api(api_client)
```

### Option 3: Request Queue with Rate Limiting
Implement a queue to limit concurrent Kubernetes API calls:
```python
# Semaphore to limit concurrent K8s API calls
k8s_semaphore = asyncio.Semaphore(10)

async def execute(request: ExecuteRequest):
    async with k8s_semaphore:
        # Create job with rate limiting
        batch_v1.create_namespaced_job(...)
```

## Recommended Fix
Combine Options 1 and 3:
1. Create per-request clients to avoid thread safety issues
2. Use a semaphore to limit concurrent API calls
3. Add retry logic with exponential backoff for API errors