#!/usr/bin/env python3
"""
Test script to verify retry logic calculations.
"""

from retry_config import (
    calculate_retry_delay,
    should_retry_http_error,
    get_retry_message,
    RetryStrategy,
)


def test_retry_delays():
    """Test exponential backoff calculations."""
    print("Testing retry delay calculations:")
    print("-" * 50)

    # Test default policy
    print("\nDefault Policy:")
    for i in range(6):
        delay = calculate_retry_delay(i, "default", add_jitter=False)
        print(f"  Retry {i}: {delay}s")

    # Test aggressive policy
    print("\nAggressive Policy:")
    for i in range(6):
        delay = calculate_retry_delay(i, "aggressive", add_jitter=False)
        print(f"  Retry {i}: {delay}s")

    # Test with jitter
    print("\nDefault Policy with Jitter:")
    for i in range(3):
        delay = calculate_retry_delay(i, "default", add_jitter=True)
        print(f"  Retry {i}: {delay}s (includes random jitter)")


def test_http_error_classification():
    """Test HTTP error classification."""
    print("\n\nTesting HTTP error classification:")
    print("-" * 50)

    test_codes = [400, 401, 404, 408, 429, 500, 502, 503, 504, 520]

    for code in test_codes:
        should_retry, reason = should_retry_http_error(code)
        status = "RETRY" if should_retry else "NO RETRY"
        print(f"  HTTP {code}: {status} - {reason}")


def test_retry_strategy():
    """Test RetryStrategy class."""
    print("\n\nTesting RetryStrategy:")
    print("-" * 50)

    strategy = RetryStrategy("default")

    # Mock exception with status code
    class MockHTTPException(Exception):
        def __init__(self, status_code):
            self.response = type("obj", (object,), {"status_code": status_code})

    # Test various scenarios
    test_cases = [
        (MockHTTPException(503), 0, True, "Service unavailable should retry"),
        (MockHTTPException(404), 0, False, "Not found should not retry"),
        (MockHTTPException(429), 2, True, "Rate limit should retry"),
        (Exception("Connection refused"), 0, True, "Connection errors should retry"),
        (MockHTTPException(503), 10, False, "Should not retry after max attempts"),
    ]

    for exc, retry_count, expected, description in test_cases:
        result = strategy.should_retry(exc, retry_count)
        status = "PASS" if result == expected else "FAIL"
        print(f"  [{status}] {description}")


def test_retry_message():
    """Test retry message formatting."""
    print("\n\nTesting retry message formatting:")
    print("-" * 50)

    message = get_retry_message("evaluate_code", "eval_123", 2, 5, 30.5, "Service Unavailable")
    print(f"  Example message:\n    {message}")


if __name__ == "__main__":
    test_retry_delays()
    test_http_error_classification()
    test_retry_strategy()
    test_retry_message()
    print("\n✅ All tests completed!")
