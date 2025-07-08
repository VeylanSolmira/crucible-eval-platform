"""
Integration tests for fast-failing container scenarios.

These tests verify that:
1. Fast-failing containers (like 1/0) properly report as "failed" 
2. Error messages are successfully captured from containers that exit quickly
3. The Docker event race condition is properly handled

Based on the debugging journey documented in:
- /docs/debugging/missing-logs-race-condition.md
- /week-4-demo/docker-logs-issue.md
"""

import pytest
import time
import requests
from typing import Dict, Any

# Test code that should fail immediately
FAST_FAILING_CODE = 'print("Before error"); 1/0'
FAST_FAILING_WITH_STDERR = '''
import sys
print("Starting calculation...", file=sys.stdout)
print("Debug info", file=sys.stderr)
result = 1/0  # This will cause immediate failure
'''


def wait_for_evaluation_completion(
    api_session: requests.Session, 
    api_base_url: str, 
    eval_id: str, 
    timeout: int = 10
) -> Dict[str, Any]:
    """Wait for an evaluation to reach a terminal state."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = api_session.get(f"{api_base_url}/eval/{eval_id}")
        if response.status_code == 200:
            result = response.json()
            status = result.get("status")
            
            # Check if we've reached a terminal state
            if status in ["completed", "failed", "timeout", "cancelled"]:
                return result
        
        time.sleep(0.5)
    
    raise TimeoutError(f"Evaluation {eval_id} did not complete within {timeout} seconds")


@pytest.mark.integration
@pytest.mark.api
def test_fast_failing_container_logs_captured(api_session: requests.Session, api_base_url: str):
    """
    Test that fast-failing containers have their logs properly captured.
    
    This verifies the fix for the Docker event race condition where containers
    that exit very quickly (< 1 second) would show as failed but with empty logs.
    """
    # Submit evaluation with code that fails immediately
    response = api_session.post(
        f"{api_base_url}/eval",
        json={
            "code": FAST_FAILING_CODE,
            "language": "python",
            "timeout": 30
        }
    )
    
    assert response.status_code == 200, f"Failed to submit evaluation: {response.text}"
    eval_id = response.json()["eval_id"]
    
    # Wait for evaluation to complete
    result = wait_for_evaluation_completion(api_session, api_base_url, eval_id)
    
    # Verify the evaluation failed as expected
    assert result["status"] == "failed", f"Expected status 'failed', got '{result['status']}'"
    
    # CRITICAL: Verify that logs were captured
    # Before the fix, both output and error would be empty strings
    error_content = result.get("error", "")
    output_content = result.get("output", "")
    
    # We should have either error content or output content (depending on implementation)
    # The current implementation puts all logs in error field when exit_code != 0
    assert error_content or output_content, (
        "No logs captured from fast-failing container! "
        "This indicates the Docker event race condition may have regressed."
    )
    
    # Verify we can see the expected error
    combined_logs = error_content + output_content
    assert "Before error" in combined_logs, "Expected stdout output not found in logs"
    assert "ZeroDivisionError" in combined_logs, "Expected error traceback not found in logs"


@pytest.mark.integration
@pytest.mark.api
def test_mixed_stdout_stderr_fast_failure(api_session: requests.Session, api_base_url: str):
    """
    Test that containers with mixed stdout/stderr output are handled correctly.
    
    Note: Current implementation mixes stdout and stderr together, which is a known
    limitation documented in /week-4-demo/docker-logs-issue.md
    """
    # Submit evaluation with code that outputs to both streams
    response = api_session.post(
        f"{api_base_url}/eval",
        json={
            "code": FAST_FAILING_WITH_STDERR,
            "language": "python",
            "timeout": 30
        }
    )
    
    assert response.status_code == 200, f"Failed to submit evaluation: {response.text}"
    eval_id = response.json()["eval_id"]
    
    # Wait for evaluation to complete
    result = wait_for_evaluation_completion(api_session, api_base_url, eval_id)
    
    # Verify the evaluation failed
    assert result["status"] == "failed"
    
    # Get all log content
    error_content = result.get("error", "")
    output_content = result.get("output", "")
    combined_logs = error_content + output_content
    
    # Verify both stdout and stderr content is present (even if mixed)
    assert "Starting calculation..." in combined_logs, "stdout content missing"
    assert "Debug info" in combined_logs, "stderr content missing"
    assert "ZeroDivisionError" in combined_logs, "exception traceback missing"


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.slow
def test_multiple_fast_failures_no_stuck_evaluations(api_session: requests.Session, api_base_url: str):
    """
    Test that multiple fast-failing containers don't cause stuck evaluations.
    
    Before the fix, fast-failing containers could get stuck in "running" state
    because their completion events were dropped.
    """
    eval_ids = []
    
    # Submit multiple fast-failing evaluations
    for i in range(5):
        response = api_session.post(
            f"{api_base_url}/eval",
            json={
                "code": f'print("Test {i}"); raise RuntimeError("Fast failure {i}")',
                "language": "python",
                "timeout": 30
            }
        )
        assert response.status_code == 200
        eval_ids.append(response.json()["eval_id"])
    
    # Wait for all evaluations to complete (they may be queued)
    max_wait = 30  # Allow up to 30 seconds for processing
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        stuck_evaluations = []
        for eval_id in eval_ids:
            response = api_session.get(f"{api_base_url}/eval/{eval_id}")
            if response.status_code == 200:
                result = response.json()
                # Only consider "running" as stuck - queued/provisioning are normal states
                if result["status"] == "running":
                    # Check if it's been running for too long
                    if result.get("runtime_ms", 0) > 5000:  # More than 5 seconds
                        stuck_evaluations.append((eval_id, result["status"]))
                elif result["status"] in ["queued", "provisioning"]:
                    # These are transitional states, not stuck
                    pass
        
        if not stuck_evaluations:
            # All evaluations have either completed or are in queue/provisioning
            break
            
        time.sleep(1)
    
    assert not stuck_evaluations, (
        f"Found {len(stuck_evaluations)} stuck evaluations: {stuck_evaluations}. "
        "This suggests the Docker event handler is not properly processing die events."
    )


@pytest.mark.integration
@pytest.mark.api
def test_extremely_fast_exit(api_session: requests.Session, api_base_url: str):
    """
    Test the most extreme case: code that exits instantly with sys.exit().
    
    This is even faster than raising an exception and tests the absolute limits
    of the race condition fix.
    """
    # Code that exits as fast as possible
    instant_exit_code = "import sys; sys.exit(42)"
    
    response = api_session.post(
        f"{api_base_url}/eval",
        json={
            "code": instant_exit_code,
            "language": "python",
            "timeout": 30
        }
    )
    
    assert response.status_code == 200
    eval_id = response.json()["eval_id"]
    
    # Wait for completion
    result = wait_for_evaluation_completion(api_session, api_base_url, eval_id)
    
    # Should be marked as failed (non-zero exit code)
    assert result["status"] == "failed", (
        f"Expected 'failed' status for sys.exit(42), got '{result['status']}'"
    )
    
    # Even for instant exits, we should not get stuck in running state
    assert result["status"] != "running", "Evaluation stuck in running state!"


if __name__ == "__main__":
    # Allow running directly for debugging
    pytest.main([__file__, "-v", "-s"])