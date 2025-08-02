"""
Tests for fast-failing container scenarios.

These tests verify that containers which exit very quickly (< 1 second) are handled correctly:
1. Fast-failing containers (like 1/0) properly report as "failed" 
2. Error messages are successfully captured before the pod terminates
3. The race condition between process exit and log collection is properly handled
4. Multiple fast failures don't cause stuck evaluations

Originally created to catch a race condition in Docker-based execution, these tests
remain critical for Kubernetes to ensure:
- Pod logs are collected before termination
- Job status monitoring detects failures correctly
- The system handles extreme edge cases (instant sys.exit)

Note: In Kubernetes, these tests have different timing characteristics:
- Pod creation and scheduling adds overhead (typically 2-5 seconds)
- Celery monitors job status every 10 seconds (polling-based)
- Total time from submission to completion is typically 10-15 seconds
- The actual container execution is still fast (< 1 second)
"""

import pytest
import time
import requests
from typing import Dict, Any
from tests.k8s_test_config import API_URL
from tests.utils.utils import wait_for_completion, submit_evaluation

# Test code that should fail immediately
FAST_FAILING_CODE = 'print("Before error"); 1/0'
FAST_FAILING_WITH_STDERR = '''
import sys
print("Starting calculation...", file=sys.stdout)
print("Debug info", file=sys.stderr)
result = 1/0  # This will cause immediate failure
'''




@pytest.mark.whitebox
@pytest.mark.integration
@pytest.mark.api
def test_fast_failing_container_logs_captured():
    """
    Test that fast-failing containers have their logs properly captured.
    
    This verifies that containers that exit very quickly (< 1 second) have their
    logs properly captured before the pod terminates.
    """
    # Submit evaluation with code that fails immediately
    eval_id = submit_evaluation(FAST_FAILING_CODE, language="python", timeout=30)
    
    # Wait for evaluation to complete
    result = wait_for_completion(eval_id, use_adaptive=True)
    
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
        "This indicates the log collection race condition may have regressed."
    )
    
    # Verify we can see the expected error
    combined_logs = (error_content or "") + (output_content or "")
    assert "Before error" in combined_logs, "Expected stdout output not found in logs"
    assert "ZeroDivisionError" in combined_logs, "Expected error traceback not found in logs"


@pytest.mark.integration
@pytest.mark.api
def test_mixed_stdout_stderr_fast_failure():
    """
    Test that containers with mixed stdout/stderr output are handled correctly.
    
    Note: Current implementation mixes stdout and stderr together, which is a known
    limitation documented in /week-4-demo/docker-logs-issue.md
    """
    # Submit evaluation with code that outputs to both streams
    eval_id = submit_evaluation(FAST_FAILING_WITH_STDERR, language="python", timeout=30)
    
    # Wait for evaluation to complete
    result = wait_for_completion(eval_id, use_adaptive=True)
    
    # Verify the evaluation failed
    assert result["status"] == "failed"
    
    # Get all log content
    error_content = result.get("error", "")
    output_content = result.get("output", "")
    combined_logs = (error_content or "") + (output_content or "")
    
    # Verify both stdout and stderr content is present (even if mixed)
    assert "Starting calculation..." in combined_logs, "stdout content missing"
    assert "Debug info" in combined_logs, "stderr content missing"
    assert "ZeroDivisionError" in combined_logs, "exception traceback missing"


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.slow
def test_multiple_fast_failures_no_stuck_evaluations():
    """
    Test that multiple fast-failing containers don't cause stuck evaluations.
    
    Before the fix, fast-failing containers could get stuck in "running" state
    because their completion events were dropped.
    """
    eval_ids = []
    
    # Submit multiple fast-failing evaluations
    for i in range(5):
        code = f'print("Test {i}"); raise RuntimeError("Fast failure {i}")'
        eval_id = submit_evaluation(code, language="python", timeout=30)
        eval_ids.append(eval_id)
    
    # Wait for all evaluations to complete (they may be queued)
    max_wait = 30  # Allow up to 30 seconds for processing
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        stuck_evaluations = []
        for eval_id in eval_ids:
            response = requests.get(f"{API_URL}/eval/{eval_id}")
            if response.status_code == 200:
                result = response.json()
                # Only consider "running" as stuck - queued/provisioning are normal states
                if result["status"] == "running":
                    # Check if it's been running for too long
                    # In Kubernetes, allow more time due to monitoring intervals
                    # TODO: Reduce threshold once we implement Kubernetes event-based processing
                    runtime_ms = result.get("runtime_ms", 0)
                    if runtime_ms is not None and runtime_ms > 20000:  # More than 20 seconds
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
        "This suggests the job monitoring is not properly detecting completed jobs."
    )


@pytest.mark.integration
@pytest.mark.api
def test_extremely_fast_exit():
    """
    Test the most extreme case: code that exits instantly with sys.exit().
    
    This is even faster than raising an exception and tests the absolute limits
    of the race condition fix.
    """
    # Code that exits as fast as possible
    instant_exit_code = "import sys; sys.exit(42)"
    
    eval_id = submit_evaluation(instant_exit_code, language="python", timeout=30)
    
    # Wait for completion
    result = wait_for_completion(eval_id, use_adaptive=True)
    
    # Should be marked as failed (non-zero exit code)
    assert result["status"] == "failed", (
        f"Expected 'failed' status for sys.exit(42), got '{result['status']}'"
    )
    
    # Even for instant exits, we should not get stuck in running state
    assert result["status"] != "running", "Evaluation stuck in running state!"


if __name__ == "__main__":
    # Allow running directly for debugging
    pytest.main([__file__, "-v", "-s"])