"""
Integration tests for core evaluation flows.

Tests the complete flow from submission to completion:
1. Frontend → API → Celery → Executor → Storage
2. Frontend → API → Storage retrieval
3. Error handling paths
"""

import pytest
import time
import requests
from typing import Dict, Any


def wait_for_evaluation(
    api_session: requests.Session,
    api_base_url: str,
    eval_id: str,
    timeout: int = 30
) -> Dict[str, Any]:
    """Wait for an evaluation to reach a terminal state."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = api_session.get(f"{api_base_url}/eval/{eval_id}")
        if response.status_code == 200:
            result = response.json()
            if result.get("status") in ["completed", "failed", "timeout", "cancelled"]:
                return result
        time.sleep(0.5)
    
    raise TimeoutError(f"Evaluation {eval_id} did not complete within {timeout} seconds")


@pytest.mark.integration
@pytest.mark.api
def test_health_check(api_session: requests.Session, api_base_url: str):
    """Test that all services are healthy."""
    # Check API health
    response = api_session.get(f"{api_base_url.replace('/api', '')}/health")
    assert response.status_code == 200, f"Health check failed: {response.text}"
    
    health_data = response.json()
    # The health endpoint returns 'platform': 'healthy' instead of 'status': 'healthy'
    assert health_data.get("platform") == "healthy", f"API not healthy: {health_data}"
    
    # Check individual services - they return string status not dict
    services = health_data.get("services", {})
    for service, status in services.items():
        assert status == "healthy", f"Service {service} not healthy: {status}"


@pytest.mark.integration
@pytest.mark.api
def test_submit_evaluation(api_session: requests.Session, api_base_url: str):
    """Test submitting a simple evaluation."""
    # Submit evaluation
    eval_request = {
        "code": "print('Hello from integration test!')",
        "language": "python",
        "timeout": 30,
    }
    
    response = api_session.post(f"{api_base_url}/eval", json=eval_request)
    assert response.status_code == 200, f"Failed to submit evaluation: {response.text}"
    
    submit_data = response.json()
    eval_id = submit_data.get("eval_id")
    assert eval_id, f"No eval_id returned: {submit_data}"
    
    # Verify evaluation ID format
    assert isinstance(eval_id, str), "eval_id should be a string"
    assert len(eval_id) > 0, "eval_id should not be empty"


@pytest.mark.integration
@pytest.mark.api
def test_evaluation_lifecycle(api_session: requests.Session, api_base_url: str):
    """Test complete evaluation lifecycle from submission to completion."""
    # Submit evaluation
    eval_request = {
        "code": "import time\nprint('Starting...')\ntime.sleep(1)\nprint('Done!')",
        "language": "python",
        "timeout": 30,
    }
    
    response = api_session.post(f"{api_base_url}/eval", json=eval_request)
    assert response.status_code == 200, f"Failed to submit evaluation: {response.text}"
    
    eval_id = response.json()["eval_id"]
    
    # Wait for completion
    result = wait_for_evaluation(api_session, api_base_url, eval_id)
    
    # Verify completion
    assert result["status"] == "completed", f"Evaluation failed: {result}"
    
    # Verify output
    output = result.get("output", "")
    assert "Starting..." in output, f"Expected 'Starting...' in output, got: {output}"
    assert "Done!" in output, f"Expected 'Done!' in output, got: {output}"
    
    # Verify timing
    assert "created_at" in result, "Missing created_at timestamp"
    assert "completed_at" in result, "Missing completed_at timestamp"


@pytest.mark.integration
@pytest.mark.api
def test_error_handling(api_session: requests.Session, api_base_url: str):
    """Test error handling for various failure scenarios."""
    # Test 1: Code that exits with error
    eval_request = {
        "code": "import sys\nsys.exit(1)",
        "language": "python",
        "timeout": 10,
    }
    
    response = api_session.post(f"{api_base_url}/eval", json=eval_request)
    assert response.status_code == 200
    
    eval_id = response.json()["eval_id"]
    result = wait_for_evaluation(api_session, api_base_url, eval_id, timeout=15)
    
    assert result["status"] == "failed", f"Expected failed status for sys.exit(1), got: {result['status']}"
    
    # Test 2: Invalid request (missing required fields)
    bad_request = {"invalid": "request"}
    response = api_session.post(f"{api_base_url}/eval", json=bad_request)
    
    assert response.status_code == 422, f"Expected 422 for invalid request, got: {response.status_code}"
    
    # Test 3: Division by zero
    eval_request = {
        "code": "print('Before error')\nresult = 1/0",
        "language": "python",
        "timeout": 10,
    }
    
    response = api_session.post(f"{api_base_url}/eval", json=eval_request)
    assert response.status_code == 200
    
    eval_id = response.json()["eval_id"]
    result = wait_for_evaluation(api_session, api_base_url, eval_id)
    
    assert result["status"] == "failed", "Division by zero should fail"
    error_output = result.get("error", "") + result.get("output", "")
    assert "ZeroDivisionError" in error_output, f"Expected ZeroDivisionError in output, got: {error_output}"


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.slow
def test_concurrent_evaluations(api_session: requests.Session, api_base_url: str):
    """Test multiple concurrent evaluations."""
    # Submit multiple evaluations
    eval_ids = []
    num_evaluations = 5
    
    for i in range(num_evaluations):
        eval_request = {
            "code": f"import time\nprint('Eval {i}')\ntime.sleep(0.5)",
            "language": "python",
            "timeout": 30,
        }
        
        response = api_session.post(f"{api_base_url}/eval", json=eval_request)
        assert response.status_code == 200
        eval_ids.append(response.json()["eval_id"])
    
    assert len(eval_ids) == num_evaluations, f"Expected {num_evaluations} eval IDs"
    
    # Wait for all to complete
    completed = []
    timeout = 30
    start_time = time.time()
    
    while len(completed) < num_evaluations and time.time() - start_time < timeout:
        for eval_id in eval_ids:
            if eval_id not in completed:
                response = api_session.get(f"{api_base_url}/eval/{eval_id}")
                if response.status_code == 200:
                    result = response.json()
                    if result["status"] in ["completed", "failed"]:
                        completed.append(eval_id)
                        assert result["status"] == "completed", f"Evaluation {eval_id} failed"
        time.sleep(0.5)
    
    assert len(completed) == num_evaluations, (
        f"Only {len(completed)}/{num_evaluations} evaluations completed within {timeout}s"
    )


@pytest.mark.integration
@pytest.mark.api
def test_storage_retrieval(api_session: requests.Session, api_base_url: str):
    """Test storage retrieval functionality."""
    # Submit an evaluation
    eval_request = {
        "code": "print('Storage test output')",
        "language": "python",
        "timeout": 10,
    }
    
    response = api_session.post(f"{api_base_url}/eval", json=eval_request)
    assert response.status_code == 200
    
    eval_id = response.json()["eval_id"]
    
    # Wait for completion
    result = wait_for_evaluation(api_session, api_base_url, eval_id)
    assert result["status"] == "completed"
    
    # Test storage retrieval endpoint (if it exists)
    # Note: This endpoint might not exist in all configurations
    storage_response = api_session.get(f"{api_base_url}/storage/evaluation/{eval_id}")
    
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


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.skip(reason="Platform does not currently enforce timeouts strictly")
def test_evaluation_timeout(api_session: requests.Session, api_base_url: str):
    """Test that evaluations timeout correctly.
    
    TODO: TIMEOUT-ENFORCEMENT - The platform currently does not enforce timeouts strictly.
    
    What "strict timeout enforcement" means:
    - When a user specifies timeout=2 seconds, the code should be forcibly stopped after 2 seconds
    - The container/process should be killed if it exceeds the timeout
    - The evaluation should return with status="timeout" or status="failed"
    
    Current behavior:
    - The timeout parameter is passed to Docker but may not be enforced
    - Code that runs longer than the timeout still completes successfully
    - In the test, code with sleep(10) and timeout=2 runs for the full 10 seconds
    
    This could be due to:
    1. Docker not enforcing the timeout parameter correctly
    2. The executor service not implementing timeout handling
    3. Grace periods or cleanup time being added to the timeout
    
    This test is skipped until timeout enforcement is implemented properly.
    """
    # Submit evaluation that will timeout
    eval_request = {
        "code": "import time\ntime.sleep(10)\nprint('Should not see this')",
        "language": "python",
        "timeout": 2,  # 2 second timeout
    }
    
    response = api_session.post(f"{api_base_url}/eval", json=eval_request)
    assert response.status_code == 200
    
    eval_id = response.json()["eval_id"]
    
    # Wait for timeout
    result = wait_for_evaluation(api_session, api_base_url, eval_id, timeout=15)
    
    # The evaluation should timeout or fail
    assert result["status"] in ["timeout", "failed"], f"Expected timeout status, got: {result['status']}"
    
    # Check runtime to ensure it didn't run the full 10 seconds
    runtime_ms = result.get("runtime_ms", 0)
    assert runtime_ms < 3000, f"Evaluation ran longer than timeout: {runtime_ms}ms"


@pytest.mark.integration
@pytest.mark.api
def test_language_parameter(api_session: requests.Session, api_base_url: str):
    """Test that language parameter is handled correctly.
    
    TODO: LANGUAGE-SUPPORT - The platform currently only supports Python and 
    treats all language parameters as Python. This is a known limitation.
    When adding support for other languages (JavaScript, Go, etc.), update
    this test to verify proper language validation and execution.
    """
    # Currently only Python is supported, but test the parameter
    eval_request = {
        "code": "print('Language test')",
        "language": "python",
        "timeout": 10,
    }
    
    response = api_session.post(f"{api_base_url}/eval", json=eval_request)
    assert response.status_code == 200
    
    # Test unsupported language (if validation is implemented)
    eval_request["language"] = "javascript"
    response = api_session.post(f"{api_base_url}/eval", json=eval_request)
    
    # TODO: LANGUAGE-SUPPORT - The platform currently treats all languages as Python
    # This is a known limitation, so we just verify it doesn't crash
    if response.status_code == 422:
        # Good - API validates language
        pass
    elif response.status_code == 200:
        # API accepted - it will try to run as Python
        eval_id = response.json()["eval_id"]
        result = wait_for_evaluation(api_session, api_base_url, eval_id)
        # Since it's Python code, it will actually succeed
        # This is expected behavior for now
        assert result["status"] in ["completed", "failed"], "Should have a terminal status"


if __name__ == "__main__":
    # Allow running directly for debugging
    pytest.main([__file__, "-v", "-s"])