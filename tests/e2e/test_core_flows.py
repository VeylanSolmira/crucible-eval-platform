"""
End-to-end tests for core evaluation flows.

Tests the complete flow from submission to completion:
1. Frontend → API → Celery → Executor → Storage
2. Frontend → API → Storage retrieval
3. Error handling paths

These are true black-box tests that interact with the system via HTTP API only.
"""

import pytest
import time
import requests
from typing import Dict, Any
from tests.k8s_test_config import API_URL
from tests.utils.utils import wait_for_completion, submit_evaluation, wait_for_logs


@pytest.mark.e2e
@pytest.mark.blackbox
@pytest.mark.api
def test_health_check():
    """Test that all services are healthy."""
    # Check API health
    # Remove trailing /api from the URL to get base service URL
    base_url = API_URL.rsplit('/api', 1)[0] if API_URL.endswith('/api') else API_URL
    response = requests.get(f"{base_url}/health")
    assert response.status_code == 200, f"Health check failed: {response.text}"
    
    health_data = response.json()
    # The health endpoint returns 'status': 'healthy'
    assert health_data.get("status") == "healthy", f"API not healthy: {health_data}"
    
    # Check individual services - they return string status not dict
    services = health_data.get("services", {})
    for service, status in services.items():
        assert status == "healthy", f"Service {service} not healthy: {status}"


@pytest.mark.e2e
@pytest.mark.api
def test_submit_evaluation():
    """Test submitting a simple evaluation."""
    # Submit evaluation
    code = "print('Hello from integration test!')"
    eval_id = submit_evaluation(code, language="python", timeout=30)
    
    # Verify evaluation ID format
    assert isinstance(eval_id, str), "eval_id should be a string"
    assert len(eval_id) > 0, "eval_id should not be empty"


@pytest.mark.e2e
@pytest.mark.api
def test_evaluation_lifecycle():
    """Test complete evaluation lifecycle from submission to completion."""
    # Submit evaluation
    code = "import time\nprint('Starting...')\ntime.sleep(1)\nprint('Done!')"
    eval_id = submit_evaluation(code, language="python", timeout=30)
    
    # Wait for completion
    result = wait_for_completion(eval_id, timeout=120, use_adaptive=True)
    
    # Verify completion
    assert result["status"] == "completed", f"Evaluation failed: {result}"
    
    # Wait for logs to be available (handles race condition)
    output = wait_for_logs(eval_id, timeout=30)
    
    # Verify output
    assert "Starting..." in output, f"Expected 'Starting...' in output, got: {output}"
    assert "Done!" in output, f"Expected 'Done!' in output, got: {output}"
    
    # Verify timing
    assert "created_at" in result, "Missing created_at timestamp"
    assert "completed_at" in result, "Missing completed_at timestamp"


@pytest.mark.e2e
@pytest.mark.api
def test_error_handling():
    """Test error handling for various failure scenarios."""
    # Test 1: Code that exits with error
    code = "import sys\nsys.exit(1)"
    eval_id = submit_evaluation(code, language="python", timeout=10, expect_failure=True)
    # Extended timeout for when cluster is under load
    result = wait_for_completion(eval_id, timeout=300, use_adaptive=True)
    
    assert result["status"] == "failed", f"Expected failed status for sys.exit(1), got: {result['status']}. Full result: {result}"
    
    # Test 2: Invalid request (missing required fields)
    bad_request = {"invalid": "request"}
    response = requests.post(f"{API_URL}/eval", json=bad_request)
    
    assert response.status_code == 422, f"Expected 422 for invalid request, got: {response.status_code}"
    
    # Test 3: Division by zero
    code = "print('Before error')\nresult = 1/0"
    eval_id = submit_evaluation(code, language="python", timeout=10, expect_failure=True)
    result = wait_for_completion(eval_id, timeout=300, use_adaptive=True)
    
    assert result["status"] == "failed", f"Division by zero should fail. Got status: {result['status']}. Full result: {result}"
    
    # For failed evaluations, check both error and output fields
    # wait_for_logs handles this internally
    try:
        output = wait_for_logs(eval_id, timeout=30)
        error_output = output
    except TimeoutError:
        # If logs timeout, fall back to checking error field directly
        error_output = result.get("error") or ""
    
    # Also check the output field if error is empty
    if not error_output:
        error_output = result.get("output") or ""
    
    # Ensure error_output is never None
    if error_output is None:
        error_output = ""
    
    assert "ZeroDivisionError" in error_output or "division by zero" in error_output.lower(), \
        f"Expected ZeroDivisionError in output, got: {repr(error_output)}. Full result: {result}"


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.slow
def test_concurrent_evaluations():
    """Test multiple concurrent evaluations."""
    # Submit multiple evaluations
    eval_ids = []
    num_evaluations = 5
    
    for i in range(num_evaluations):
        code = f"import time\nprint('Eval {i}')\ntime.sleep(0.5)"
        eval_id = submit_evaluation(code, language="python", timeout=30)
        eval_ids.append(eval_id)
    
    assert len(eval_ids) == num_evaluations, f"Expected {num_evaluations} eval IDs"
    
    # Wait for all to complete with adaptive waiting
    completed = 0
    failed = []
    
    for eval_id in eval_ids:
        # Extended timeout for when cluster is under load
        result = wait_for_completion(eval_id, timeout=120, use_adaptive=True)
        if result["status"] == "completed":
            completed += 1
        else:
            failed.append((eval_id, result["status"]))
    
    assert completed == num_evaluations, (
        f"Only {completed}/{num_evaluations} evaluations completed. "
        f"Failed: {failed}"
    )


@pytest.mark.e2e
@pytest.mark.api
def test_storage_retrieval():
    """Test storage retrieval functionality."""
    # Submit an evaluation
    code = "print('Storage test output')"
    eval_id = submit_evaluation(code, language="python", timeout=10)
    
    # Wait for completion
    result = wait_for_completion(eval_id, timeout=120, use_adaptive=True)
    assert result["status"] == "completed", f"Expected completed status, got: {result['status']}. Full result: {result}"
    
    # Wait for logs to be available
    output = wait_for_logs(eval_id, timeout=30)
    assert "Storage test output" in output, f"Expected 'Storage test output' in output, got: {output}"
    
    # Test evaluation retrieval through standard endpoint
    eval_response = requests.get(f"{API_URL}/eval/{eval_id}")
    assert eval_response.status_code == 200, f"Failed to retrieve evaluation: {eval_response.status_code}"
    
    eval_data = eval_response.json()
    assert eval_data.get("eval_id") == eval_id, "Eval ID mismatch"
    assert eval_data.get("status") == "completed", f"Unexpected status: {eval_data.get('status')}"
    assert eval_data.get("output"), "Missing output in evaluation data"


@pytest.mark.e2e
@pytest.mark.api
def test_evaluation_timeout():
    """Test that evaluations timeout correctly.
    
    Kubernetes DOES enforce timeouts via activeDeadlineSeconds:
    - When timeout is exceeded, Kubernetes sends SIGTERM to the pod
    - After terminationGracePeriodSeconds (1s), it sends SIGKILL
    - The job is marked as failed with DeadlineExceeded
    
    Current limitations:
    - Python processes don't handle SIGTERM, so they run until SIGKILL
    - Celery polls every 10 seconds, so runtime reporting is delayed
    - The reported runtime may show up to ~10 seconds even though the job was killed earlier
    
    TODO: When we implement Kubernetes event-based status updates, the runtime
    reporting will be accurate to when the job was actually terminated.
    """
    # Submit evaluation that will timeout
    # Note: expect_failure=True prevents Kubernetes retry attempts (backoffLimit=0)
    # Without this, K8s would retry 3 times with exponential backoff, taking 30+ seconds
    code = "import time\ntime.sleep(10)\nprint('Should not see this')"
    eval_id = submit_evaluation(code, language="python", timeout=2, expect_failure=True)  # 2 second timeout, no retries
    
    # Wait for timeout - need to wait longer than the 2 second timeout plus overhead
    result = wait_for_completion(eval_id, timeout=30, use_adaptive=True)
    
    # The evaluation should timeout or fail
    assert result["status"] in ["timeout", "failed"], f"Expected timeout status, got: {result['status']}"
    
    # NOTE: Due to Celery's 10-second polling interval, the reported runtime may be up to 10 seconds
    # longer than the actual timeout. Kubernetes DOES enforce the timeout (activeDeadlineSeconds),
    # but Celery only detects the failure on its next poll cycle.
    # TODO: This will be fixed when we implement Kubernetes event-based status updates
    # We don't assert on exact timing because it varies with cluster load, preemption, etc.
    # Just verify that the timeout was enforced (status is timeout/failed)
    # TODO: Implement adaptive timeout checking based on cluster load


@pytest.mark.e2e
@pytest.mark.api
def test_language_parameter():
    """Test that language parameter is handled correctly.
    
    TODO: LANGUAGE-SUPPORT - The platform currently only supports Python and 
    treats all language parameters as Python. This is a known limitation.
    When adding support for other languages (JavaScript, Go, etc.), update
    this test to verify proper language validation and execution.
    """
    # Currently only Python is supported, but test the parameter
    code = "print('Language test')"
    eval_id = submit_evaluation(code, language="python", timeout=10)
    # If we get here, submission was successful
    
    # Test unsupported language (if validation is implemented)
    # Note: We need to use direct API call here to test invalid language parameter
    eval_request = {
        "code": "print('Language test')",
        "language": "javascript",
        "timeout": 10,
    }
    response = requests.post(f"{API_URL}/eval", json=eval_request)
    
    # TODO: LANGUAGE-SUPPORT - The platform currently treats all languages as Python
    # This is a known limitation, so we just verify it doesn't crash
    if response.status_code == 422:
        # Good - API validates language
        pass
    elif response.status_code == 200:
        # API accepted - it will try to run as Python
        eval_id = response.json()["eval_id"]
        result = wait_for_completion(eval_id, timeout=120, use_adaptive=True)
        # Since it's Python code, it will actually succeed
        # This is expected behavior for now
        assert result["status"] in ["completed", "failed"], "Should have a terminal status"


if __name__ == "__main__":
    # Allow running directly for debugging
    pytest.main([__file__, "-v", "-s"])