# Kubernetes ResourceQuota Handling for Job Creation

## Problem Statement

When the Kubernetes cluster reaches its ResourceQuota limits (e.g., maximum number of jobs), new job creation requests fail with:
- **Status Code**: 403 Forbidden
- **Error Message**: `jobs.batch "job-name" is forbidden: exceeded quota: evaluation-quota, requested: count/jobs.batch=1, used: count/jobs.batch=50, limited: count/jobs.batch=50`

Currently, our Celery worker treats 403 errors as non-retryable client errors, causing evaluations to permanently fail when they should be retried once resources become available.

## Current Architecture

```
User -> API -> Celery -> Dispatcher -> Kubernetes API
                 ^                          |
                 |                          v
                 +-- 403 (No Retry) --------+
```

## Solution Options

### Option 1: Parse Error Body in Dispatcher (Immediate Fix)
**Implementation**: Check if 403 errors contain "exceeded quota" and return 429 instead
- **Pros**: 
  - Quick to implement
  - Celery already retries 429 errors
  - Minimal code changes
- **Cons**: 
  - Fragile - relies on error message text
  - Could break if Kubernetes changes error format

### Option 2: Job Queue in Dispatcher
**Implementation**: Dispatcher maintains internal queue when quota exceeded
- **Pros**:
  - More robust than parsing error messages
  - Can check quota before attempting creation
  - Better user experience (202 Accepted)
- **Cons**:
  - More complex implementation
  - Need to handle dispatcher restarts/persistence
  - Adds another queue layer

### Option 3: Kubernetes Job Queue System
**Implementation**: Use Kueue, Volcano, or similar job queuing system
- **Pros**:
  - Production-grade solution
  - Handles many edge cases
  - Fair scheduling across users/priorities
- **Cons**:
  - Additional infrastructure to deploy/maintain
  - Learning curve
  - May be overkill for current scale

### Option 4: Configure Celery to Retry 403
**Implementation**: Add 403 to retryable status codes in Celery
- **Pros**:
  - Simplest solution
  - No dispatcher changes needed
- **Cons**:
  - Will retry ALL 403 errors (not just quota)
  - Less semantic - 403 usually means "forbidden", not "try later"

### Option 5: Proactive Quota Monitoring
**Implementation**: Watch ResourceQuota objects and prevent creation when near limits
- **Pros**:
  - Prevents hitting limits in first place
  - Can provide better error messages
  - More efficient than retrying
- **Cons**:
  - Complex to implement correctly
  - Race conditions with other job creators
  - Need to handle quota changes

## Recommendation

For immediate relief, implement **Option 1** (parse error body) as it:
- Solves the immediate problem
- Requires minimal changes
- Uses existing retry infrastructure

For long-term production use, consider migrating to **Option 3** (Kubernetes job queue) as it:
- Provides proper queueing semantics
- Handles fair scheduling
- Is battle-tested for production workloads

## Implementation Details

### Option 1 Implementation (Current Choice)

```python
# In dispatcher_service/app.py
except ApiException as e:
    logger.error(f"Failed to create job {job_name}: {e}")
    
    # Check if this is a ResourceQuota error
    if e.status == 403 and "exceeded quota" in str(e.body):
        # Return 429 (Too Many Requests) for quota errors so Celery will retry
        raise HTTPException(
            status_code=429,
            detail=f"Resource quota exceeded - too many jobs. Please wait and retry."
        )
    
    raise HTTPException(
        status_code=e.status,
        detail=f"Kubernetes API error: {e.reason}"
    )
```

This causes Celery to automatically retry with exponential backoff, as 429 is already configured as a retryable error.

## Testing

To test ResourceQuota handling:
1. Set a low quota: `kubectl edit resourcequota evaluation-quota -n crucible`
2. Submit many evaluations to exceed quota
3. Verify tasks are retried instead of failing
4. Clean up old jobs to free quota
5. Verify retried tasks eventually succeed

## Future Considerations

- Monitor retry rates to detect quota pressure
- Consider implementing Option 2 or 3 if retry storms become a problem
- Add metrics for quota usage and wait times
- Implement fair queuing if multiple users compete for resources