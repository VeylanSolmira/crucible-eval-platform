"""
Retry configuration and policies for Celery tasks.

This module defines retry strategies for different types of failures,
implementing exponential backoff with jitter to prevent thundering herd.
"""
import random
from typing import Optional, Tuple
# from celery.exceptions import Retry  # Not needed for core functionality

# Retry policy configurations
RETRY_POLICIES = {
    'default': {
        'max_retries': 5,
        'base_delay': 2,
        'max_delay': 300,  # 5 minutes
        'exponential_base': 2,
        'jitter': True,
    },
    'aggressive': {
        'max_retries': 10,
        'base_delay': 1,
        'max_delay': 600,  # 10 minutes
        'exponential_base': 1.5,
        'jitter': True,
    },
    'conservative': {
        'max_retries': 3,
        'base_delay': 5,
        'max_delay': 60,  # 1 minute
        'exponential_base': 2,
        'jitter': False,
    },
}

# Error categories that determine retry behavior
RETRYABLE_HTTP_CODES = {
    408: 'Request Timeout',
    429: 'Too Many Requests',
    500: 'Internal Server Error',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
}

NON_RETRYABLE_HTTP_CODES = {
    400: 'Bad Request',
    401: 'Unauthorized',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    409: 'Conflict',
    410: 'Gone',
    422: 'Unprocessable Entity',
}

def calculate_retry_delay(
    retry_count: int,
    policy: str = 'default',
    add_jitter: Optional[bool] = None
) -> float:
    """
    Calculate retry delay based on policy and retry count.
    
    Args:
        retry_count: Current retry attempt (0-based)
        policy: Name of retry policy to use
        add_jitter: Override jitter setting from policy
        
    Returns:
        Delay in seconds before next retry
    """
    config = RETRY_POLICIES.get(policy, RETRY_POLICIES['default'])
    
    base_delay = config['base_delay']
    exponential_base = config['exponential_base']
    max_delay = config['max_delay']
    use_jitter = add_jitter if add_jitter is not None else config['jitter']
    
    # Calculate exponential backoff
    delay = base_delay * (exponential_base ** retry_count)
    
    # Cap at maximum delay
    delay = min(delay, max_delay)
    
    # Add jitter to prevent thundering herd
    if use_jitter:
        # Add 0-25% random jitter
        jitter = delay * random.uniform(0, 0.25)
        delay += jitter
    
    return round(delay, 2)

def should_retry_http_error(status_code: int) -> Tuple[bool, str]:
    """
    Determine if an HTTP error should be retried.
    
    Args:
        status_code: HTTP status code
        
    Returns:
        Tuple of (should_retry, reason)
    """
    if status_code in RETRYABLE_HTTP_CODES:
        return True, RETRYABLE_HTTP_CODES[status_code]
    elif status_code in NON_RETRYABLE_HTTP_CODES:
        return False, NON_RETRYABLE_HTTP_CODES[status_code]
    elif 500 <= status_code < 600:
        return True, 'Server Error'
    else:
        return False, 'Unknown Error'

def get_retry_message(
    task_name: str,
    eval_id: str,
    retry_count: int,
    max_retries: int,
    delay: float,
    reason: str
) -> str:
    """
    Generate a consistent retry log message.
    
    Args:
        task_name: Name of the Celery task
        eval_id: Evaluation ID
        retry_count: Current retry attempt
        max_retries: Maximum retry attempts
        delay: Delay before next retry
        reason: Reason for retry
        
    Returns:
        Formatted log message
    """
    return (
        f"Task {task_name} for evaluation {eval_id} failed: {reason}. "
        f"Retry {retry_count + 1}/{max_retries} in {delay}s"
    )

class RetryStrategy:
    """
    Encapsulate retry logic for different failure scenarios.
    """
    
    def __init__(self, policy: str = 'default'):
        self.policy = policy
        self.config = RETRY_POLICIES.get(policy, RETRY_POLICIES['default'])
    
    def should_retry(self, exception: Exception, retry_count: int) -> bool:
        """Determine if task should be retried based on exception."""
        if retry_count >= self.config['max_retries']:
            return False
            
        # Check specific exception types
        if hasattr(exception, 'response'):
            status_code = getattr(exception.response, 'status_code', None)
            if status_code:
                should_retry, _ = should_retry_http_error(status_code)
                return should_retry
        
        # Retry on connection errors
        if any(err in str(exception).lower() for err in ['connection', 'timeout', 'refused']):
            return True
            
        return False
    
    def get_retry_delay(self, retry_count: int) -> float:
        """Get delay for next retry attempt."""
        return calculate_retry_delay(retry_count, self.policy)