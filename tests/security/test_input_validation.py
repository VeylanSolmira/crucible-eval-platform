#!/usr/bin/env python3
"""
Security tests for input validation and sanitization.
Tests that the API properly rejects dangerous or malformed inputs.

WARNING: These tests intentionally send malformed and oversized requests to test
the API's resilience. This may:
- Generate large error logs
- Consume temporary memory/disk space
- Trigger rate limiting if enabled
- Impact API performance during test execution

It's recommended to run these tests against a dedicated test environment.
"""

import pytest
import requests
import json
from typing import Dict, Any

# Import from local conftest
from conftest import get_api_url, get_request_config
from tests.utils.utils import submit_evaluation, get_evaluation_status


@pytest.mark.blackbox
@pytest.mark.integration
@pytest.mark.api
@pytest.mark.security
class TestInputValidation:
    """Test that dangerous inputs are properly rejected"""

    def test_code_size_limit(self):
        """Verify oversized code submissions are rejected to prevent DoS"""
        # WARNING: This creates a ~6MB payload
        # Adjust size if this causes issues in your environment
        large_code = "x = 1\n" * 1_000_000  # ~6MB of code
        
        response = requests.post(
            f"{get_api_url()}/eval",
            json={
                "code": large_code,
                "language": "python",
                "timeout": 30,
                "priority": -1  # Low priority for test
            },
            **get_request_config()
        )
        
        # Should reject with 413 or 400
        assert response.status_code in [400, 413], "Large payloads should be rejected"

    def test_malformed_json_rejected(self):
        """Verify malformed JSON is properly rejected"""
        # Send invalid JSON
        response = requests.post(
            f"{get_api_url()}/eval",
            data='{"code": "print(\"test\")',  # Missing closing brace
            headers={"Content-Type": "application/json"},
            **get_request_config()
        )
        
        assert response.status_code == 422, "Malformed JSON should return 422 (FastAPI validation error)"

    def test_missing_required_fields(self):
        """Verify requests missing required fields are rejected"""
        # Missing 'code' field
        response = requests.post(
            f"{get_api_url()}/eval",
            json={
                "language": "python",
                "timeout": 30,
                "priority": -1
            },
            **get_request_config()
        )
        
        assert response.status_code == 422, "Missing required fields should return 422"

    def test_invalid_language_rejected(self):
        """Verify only supported languages are accepted"""
        response = requests.post(
            f"{get_api_url()}/eval",
            json={
                "code": "print('test')",
                "language": "malicious-lang",
                "timeout": 30,
                "priority": -1
            },
            **get_request_config()
        )
        
        assert response.status_code in [400, 422], "Invalid language should be rejected"

    def test_negative_timeout_rejected(self):
        """Verify invalid timeout values are rejected"""
        response = requests.post(
            f"{get_api_url()}/eval",
            json={
                "code": "print('test')",
                "language": "python",
                "timeout": -1,
                "priority": -1
            },
            **get_request_config()
        )
        
        assert response.status_code in [400, 422], "Negative timeout should be rejected"

    def test_excessive_timeout_rejected(self):
        """Verify excessively long timeouts are rejected"""
        response = requests.post(
            f"{get_api_url()}/eval",
            json={
                "code": "print('test')",
                "language": "python",
                "timeout": 3600,  # 1 hour
                "priority": -1
            },
            **get_request_config()
        )
        
        assert response.status_code in [400, 422], "Excessive timeout should be rejected"

    def test_null_byte_injection(self):
        """Verify null bytes in input are handled safely"""
        response = requests.post(
            f"{get_api_url()}/eval",
            json={
                "code": "print('test\\x00'); import os",
                "language": "python",
                "timeout": 30,
                "priority": -1
            },
            **get_request_config()
        )
        
        # Should either reject or handle safely
        if response.status_code == 200:
            # If accepted, verify null byte doesn't cause issues
            result = response.json()
            assert "eval_id" in result

    def test_unicode_handling(self):
        """Verify Unicode edge cases are handled properly"""
        # Various Unicode edge cases
        test_cases = [
            "print('emoji: 😈')",  # Emoji
            "print('זה טקסט בעברית')",  # RTL text
            "print('\u202e\u202dmalicious')",  # Unicode direction override
            "x = '\\ufeff'"  # Zero-width no-break space
        ]
        
        for code in test_cases:
            response = requests.post(
                f"{get_api_url()}/eval",
                json={
                    "code": code,
                    "language": "python",
                    "timeout": 30,
                    "priority": -1
                },
                **get_request_config()
            )
            
            # Should handle gracefully (accept or reject consistently)
            assert response.status_code in [200, 400, 422]

    def test_quota_error_handling(self):
        """Test that quota exhaustion provides clear error messages."""
        from tests.utils.utils import submit_evaluation, get_evaluation_status
        
        # Try to submit a job with excessive resource requests
        # This should fail at the API level with proper validation
        try:
            # This should raise an exception due to excessive resources
            eval_id = submit_evaluation(
                code='print("Excessive resource test")',
                language="python",
                timeout=10,
                cpu_limit="100",  # 100 CPUs - should exceed any reasonable limit
                memory_limit="1000Gi",  # 1TB - should exceed limit
                priority=-1  # Low priority for test
            )
            
            # If we somehow get an eval_id, check its status
            if eval_id:
                status = get_evaluation_status(eval_id)
                assert status.get("status") == "failed", "Excessive resource request should fail"
                assert "resource" in status.get("error", "").lower() or "quota" in status.get("error", "").lower()
            else:
                pytest.fail("Expected exception for excessive resources, but got None eval_id")
                
        except requests.exceptions.HTTPError as e:
            # Expected - API should reject with 400
            assert e.response.status_code == 400
            error_detail = e.response.json().get("detail", "")
            assert any(word in error_detail.lower() for word in ["resource", "limit", "exceed", "quota"]), \
                f"Error message should mention resource limits, got: {error_detail}"
        except Exception as e:
            # Other exceptions might indicate the request was rejected at submission
            assert any(word in str(e).lower() for word in ["resource", "limit", "exceed", "quota"]), \
                f"Error should mention resource limits, got: {e}"


if __name__ == "__main__":
    # Run basic validation test
    print("Testing input validation...")
    
    # Simple test that can run without pytest
    response = requests.post(
        f"{get_api_url()}/eval",
        json={
            "code": "x" * 1_000_000,  # 1MB of code
            "language": "python",
            "timeout": 30,
            "priority": -1
        },
        **get_request_config()
    )
    
    if response.status_code in [400, 413]:
        print("✅ PASS: Large payload rejected")
    else:
        print(f"❌ FAIL: Large payload accepted with status {response.status_code}")