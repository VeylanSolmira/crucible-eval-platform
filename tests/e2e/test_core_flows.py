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
from tests.utils.utils import wait_for_completion, submit_evaluation


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
    result = wait_for_completion(eval_id, use_adaptive=True)
    
    # Verify completion
    assert result["status"] == "completed", f"Evaluation failed: {result}"
    
    # Verify output
    output = result.get("output", "")
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
    eval_id = submit_evaluation(code, language="python", timeout=10)
    result = wait_for_completion(eval_id, timeout=15, use_adaptive=True)
    
    assert result["status"] == "failed", f"Expected failed status for sys.exit(1), got: {result['status']}"
    
    # Test 2: Invalid request (missing required fields)
    bad_request = {"invalid": "request"}
    response = requests.post(f"{API_URL}/eval", json=bad_request)
    
    assert response.status_code == 422, f"Expected 422 for invalid request, got: {response.status_code}"
    
    # Test 3: Division by zero
    code = "print('Before error')\nresult = 1/0"
    eval_id = submit_evaluation(code, language="python", timeout=10)
    result = wait_for_completion(eval_id, use_adaptive=True)
    
    assert result["status"] == "failed", "Division by zero should fail"
    error_output = (result.get("error") or "") + (result.get("output") or "")
    assert "ZeroDivisionError" in error_output, f"Expected ZeroDivisionError in output, got: {error_output}"


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
        result = wait_for_completion(eval_id, timeout=30, use_adaptive=True)
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
    result = wait_for_completion(eval_id, use_adaptive=True)
    assert result["status"] == "completed"
    
    # Test storage retrieval endpoint (if it exists)
    # Note: This endpoint might not exist in all configurations
    storage_response = requests.get(f"{API_URL}/storage/evaluation/{eval_id}")
    
    if storage_response.status_code == 200:
        storage_data = storage_response.json()
        assert storage_data.get("eval_id") == eval_id, "Storage eval_id mismatch"
        assert "Storage test output" in storage_data.get("output", ""), "Output not stored correctly"
    elif storage_response.status_code == 404:
        # Storage endpoint might not be exposed, which is okay
        # We can still verify through the regular eval endpoint
        assert "Storage test output" in result.get("output", ""), "Output not available"
    else:
        pytest.fail(f"Unexpected storage response: {storage_response.status_code}")


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
    code = "import time\ntime.sleep(10)\nprint('Should not see this')"
    eval_id = submit_evaluation(code, language="python", timeout=2)  # 2 second timeout
    
    # Wait for timeout - need to wait longer than the 2 second timeout plus overhead
    result = wait_for_completion(eval_id, timeout=30, use_adaptive=True)
    
    # The evaluation should timeout or fail
    assert result["status"] in ["timeout", "failed"], f"Expected timeout status, got: {result['status']}"
    
    # NOTE: Due to Celery's 10-second polling interval, the reported runtime may be up to 10 seconds
    # longer than the actual timeout. Kubernetes DOES enforce the timeout (activeDeadlineSeconds),
    # but Celery only detects the failure on its next poll cycle.
    # TODO: This will be fixed when we implement Kubernetes event-based status updates
    runtime_ms = result.get("runtime_ms")
    # Accept runtime up to 15 seconds (2s timeout + 10s polling + overhead)
    # runtime_ms can be None if evaluation failed before starting
    if runtime_ms is not None:
        assert runtime_ms < 15000, f"Evaluation ran much longer than expected: {runtime_ms}ms"


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
        result = wait_for_completion(eval_id, use_adaptive=True)
        # Since it's Python code, it will actually succeed
        # This is expected behavior for now
        assert result["status"] in ["completed", "failed"], "Should have a terminal status"


if __name__ == "__main__":
    # Allow running directly for debugging
    pytest.main([__file__, "-v", "-s"])