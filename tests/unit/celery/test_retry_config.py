#!/usr/bin/env python3
"""
Unit tests for Celery retry configuration logic.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "celery-worker"))

from retry_config import calculate_retry_delay, get_retry_message, RETRYABLE_HTTP_CODES


class TestRetryConfig:
    """Test retry configuration logic."""
    
    def test_calculate_retry_delay(self):
        """Test exponential backoff calculation."""
        # Test without jitter for predictable results
        assert calculate_retry_delay(1, add_jitter=False) == 2
        
        # Second retry: 2^2 = 4 seconds  
        assert calculate_retry_delay(2, add_jitter=False) == 4
        
        # Third retry: 2^3 = 8 seconds
        assert calculate_retry_delay(3, add_jitter=False) == 8
        
        # Max retry (5): 2^5 = 32 seconds
        assert calculate_retry_delay(5, add_jitter=False) == 32
        
        # Test with jitter - should be within expected range
        with_jitter = calculate_retry_delay(1, add_jitter=True)
        assert 2 <= with_jitter <= 2.5  # 2 + up to 25%
    
    def test_get_retry_message(self):
        """Test retry message generation."""
        msg = get_retry_message(
            task_name="test_task",
            eval_id="test_123", 
            retry_count=0,  # 0-based, so this is retry 1
            max_retries=5,
            delay=2.0,
            reason="404 Not Found"
        )
        assert "Retry 1/5" in msg
        assert "404" in msg
        assert "2.0s" in msg
        
        msg = get_retry_message(
            task_name="test_task",
            eval_id="test_456", 
            retry_count=2,  # 0-based, so this is retry 3
            max_retries=5,
            delay=8.0,
            reason="503 Service Unavailable"
        )
        assert "Retry 3/5" in msg
        assert "503" in msg
        assert "8.0s" in msg
    
    def test_retryable_http_codes(self):
        """Test retryable HTTP status codes."""
        # These should be retryable
        assert 408 in RETRYABLE_HTTP_CODES  # Request Timeout
        assert 429 in RETRYABLE_HTTP_CODES  # Too Many Requests
        assert 500 in RETRYABLE_HTTP_CODES  # Internal Server Error
        assert 502 in RETRYABLE_HTTP_CODES  # Bad Gateway
        assert 503 in RETRYABLE_HTTP_CODES  # Service Unavailable
        assert 504 in RETRYABLE_HTTP_CODES  # Gateway Timeout
        
        # These should NOT be retryable
        assert 400 not in RETRYABLE_HTTP_CODES  # Bad Request
        assert 401 not in RETRYABLE_HTTP_CODES  # Unauthorized
        assert 403 not in RETRYABLE_HTTP_CODES  # Forbidden
        assert 404 not in RETRYABLE_HTTP_CODES  # Not Found