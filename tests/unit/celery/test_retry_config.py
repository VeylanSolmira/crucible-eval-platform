#!/usr/bin/env python3
"""
Unit tests for Celery retry configuration logic.
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "celery-worker"))

from retry_config import (
    calculate_retry_delay, 
    get_retry_message, 
    RETRYABLE_HTTP_CODES,
    should_retry_http_error,
    RetryStrategy
)


@pytest.mark.unit
class TestRetryConfig:
    """Test retry configuration logic."""
    
    def test_calculate_retry_delay(self):
        """Test exponential backoff calculation."""
        # Test without jitter for predictable results
        # Default policy uses base_delay=2
        assert calculate_retry_delay(0, add_jitter=False) == 2  # First retry: 2^0 * 2 = 2
        assert calculate_retry_delay(1, add_jitter=False) == 4  # Second retry: 2^1 * 2 = 4
        assert calculate_retry_delay(2, add_jitter=False) == 8  # Third retry: 2^2 * 2 = 8
        assert calculate_retry_delay(3, add_jitter=False) == 16  # Fourth retry: 2^3 * 2 = 16
        assert calculate_retry_delay(4, add_jitter=False) == 32  # Fifth retry: 2^4 * 2 = 32
        
        # Test with jitter - should be within expected range
        with_jitter = calculate_retry_delay(0, add_jitter=True)
        assert 2 <= with_jitter <= 2.5  # 2 + up to 25%
        
        with_jitter = calculate_retry_delay(1, add_jitter=True)
        assert 4 <= with_jitter <= 5  # 4 + up to 25%
    
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
    
    def test_calculate_retry_delay_with_policies(self):
        """Test retry delay calculation with different policies."""
        # Test aggressive policy (shorter delays, base=1, exponential_base=1.5)
        assert calculate_retry_delay(0, "aggressive", add_jitter=False) == 1     # 1 * (1.5^0) = 1
        assert calculate_retry_delay(1, "aggressive", add_jitter=False) == 1.5   # 1 * (1.5^1) = 1.5
        assert calculate_retry_delay(2, "aggressive", add_jitter=False) == 2.25  # 1 * (1.5^2) = 2.25
        
        # Test default policy
        assert calculate_retry_delay(0, "default", add_jitter=False) == 2
        assert calculate_retry_delay(1, "default", add_jitter=False) == 4
        assert calculate_retry_delay(2, "default", add_jitter=False) == 8
    
    def test_should_retry_http_error(self):
        """Test HTTP error classification for retry logic."""
        # Test retryable errors
        should_retry, reason = should_retry_http_error(503)
        assert should_retry is True
        assert "Service Unavailable" in reason
        
        should_retry, reason = should_retry_http_error(429)
        assert should_retry is True
        assert "Too Many Requests" in reason  # Match actual message from retry_config.py
        
        should_retry, reason = should_retry_http_error(504)
        assert should_retry is True
        assert "Gateway Timeout" in reason
        
        # Test non-retryable errors
        should_retry, reason = should_retry_http_error(404)
        assert should_retry is False
        assert "Not Found" in reason
        
        should_retry, reason = should_retry_http_error(400)
        assert should_retry is False
        assert "Bad Request" in reason
        
        should_retry, reason = should_retry_http_error(401)
        assert should_retry is False
        assert "Unauthorized" in reason
    
    def test_retry_strategy_class(self):
        """Test RetryStrategy class functionality."""
        strategy = RetryStrategy("default")
        
        # Mock exception with status code
        class MockHTTPException(Exception):
            def __init__(self, status_code):
                self.response = type("obj", (object,), {"status_code": status_code})
        
        # Test retryable HTTP errors
        assert strategy.should_retry(MockHTTPException(503), 0) is True
        assert strategy.should_retry(MockHTTPException(429), 2) is True
        
        # Test non-retryable HTTP errors
        assert strategy.should_retry(MockHTTPException(404), 0) is False
        assert strategy.should_retry(MockHTTPException(400), 0) is False
        
        # Test max retries exceeded
        assert strategy.should_retry(MockHTTPException(503), 10) is False
        
        # Test connection errors (should always retry within limits)
        assert strategy.should_retry(Exception("Connection refused"), 0) is True
        assert strategy.should_retry(ConnectionError("Connection timeout"), 2) is True