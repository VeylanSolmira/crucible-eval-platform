# Celery Retry Logic Implementation

## Overview

Our Celery tasks implement sophisticated retry logic with exponential backoff and jitter to handle transient failures gracefully while preventing thundering herd problems.

## Key Features

### 1. Exponential Backoff
- Delays increase exponentially with each retry attempt
- Prevents overwhelming failing services
- Configurable base delay and exponential factor

### 2. Jitter
- Adds randomness (0-25%) to retry delays
- Prevents synchronized retry storms
- Critical for distributed systems

### 3. Smart HTTP Error Classification
- Retryable errors (408, 429, 5xx)
- Non-retryable errors (4xx except timeouts/rate limits)
- Connection errors always retry

### 4. Multiple Retry Policies

#### Default Policy
```python
{
    'max_retries': 5,
    'base_delay': 2,
    'max_delay': 300,  # 5 minutes
    'exponential_base': 2,
    'jitter': True,
}
```

#### Aggressive Policy
- More retries (10)
- Shorter initial delay (1s)
- Slower growth (1.5x)
- For critical operations

#### Conservative Policy
- Fewer retries (3)
- Longer initial delay (5s)
- No jitter
- For expensive operations

## Implementation

### retry_config.py
```python
from retry_config import (
    calculate_retry_delay,
    should_retry_http_error,
    get_retry_message,
    RetryStrategy
)
```

### Usage in Celery Tasks
```python
@app.task(
    bind=True,
    max_retries=5,
    autoretry_for=(httpx.HTTPError, httpx.ConnectTimeout),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def evaluate_code(self, eval_id: str, code: str):
    try:
        # Task logic
    except httpx.HTTPError as e:
        if hasattr(e, 'response') and e.response:
            status_code = e.response.status_code
            
            # Smart retry decision based on HTTP status
            if 400 <= status_code < 500:
                if status_code in [408, 429]:
                    # Retry timeouts and rate limits
                    delay = calculate_retry_delay(
                        self.request.retries,
                        'aggressive' if status_code == 429 else 'default'
                    )
                    raise self.retry(exc=e, countdown=delay)
                else:
                    # Don't retry client errors
                    raise
```

## Testing

Use `test_retry_logic.py` to verify:
```bash
python test_retry_logic.py
```

Output shows:
- Exponential delay calculations
- HTTP error classification
- Retry strategy decisions
- Message formatting

## Best Practices

### 1. Choose the Right Policy
- **Default**: General purpose
- **Aggressive**: Critical paths, external APIs
- **Conservative**: Resource-intensive operations

### 2. Log Appropriately
```python
message = get_retry_message(
    task_name='evaluate_code',
    eval_id=eval_id,
    retry_count=retry_count,
    max_retries=max_retries,
    delay=delay,
    reason='Service Unavailable'
)
logger.warning(message)
```

### 3. Handle Final Failures
```python
except Exception as e:
    if self.request.retries >= self.max_retries:
        # Final failure - update status, alert, etc.
        logger.error(f"Task failed after {self.max_retries} retries")
```

### 4. Monitor Retry Patterns
- Track retry rates
- Alert on excessive retries
- Identify systematic failures

## Common Scenarios

### Rate Limiting (429)
- Use aggressive policy
- Respect Retry-After headers
- Consider circuit breakers

### Service Unavailable (503)
- Standard exponential backoff
- May indicate deployment/scaling
- Monitor for patterns

### Timeouts (408, 504)
- Could be transient network issues
- May need timeout adjustment
- Consider regional failover

### Connection Errors
- Always retry with backoff
- May indicate network partition
- Check service discovery

## Interview Discussion Points

1. **Why exponential backoff?**
   - Linear doesn't give services time to recover
   - Prevents cascade failures
   - Industry standard practice

2. **Why add jitter?**
   - Thundering herd prevention
   - Learned from AWS/Google practices
   - Critical at scale

3. **How to choose retry limits?**
   - Balance reliability vs resource usage
   - Consider timeout budgets
   - SLA requirements

4. **Alternative approaches?**
   - Circuit breakers (fail fast)
   - Bulkheads (isolation)
   - Hedged requests (parallel attempts)