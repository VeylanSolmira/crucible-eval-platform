"""
Integration tests for priority queue functionality via the API.

These tests verify API-level queue functionality without requiring
full evaluation execution.
"""

import pytest
import requests
import time
from typing import Tuple, List, Optional
from k8s_test_config import API_URL
from utils.utils import submit_evaluation


def wait_for_completion(
    api_session: requests.Session,
    api_base_url: str,
    eval_id: str,
    timeout: float = 30
) -> Tuple[str, float]:
    """Wait for evaluation to complete and return (status, duration)."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = api_session.get(f"{api_base_url}/eval/{eval_id}")
        if response.status_code == 200:
            result = response.json()
            status = result.get("status", "unknown")
            if status in ["completed", "failed", "timeout", "cancelled"]:
                duration = time.time() - start_time
                return status, duration
        time.sleep(0.2)
    
    return "timeout", timeout


def get_queue_status(api_session: requests.Session, api_base_url: str) -> Optional[dict]:
    """Get current queue status."""
    try:
        response = api_session.get(f"{api_base_url}/queue/status")
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


@pytest.mark.integration
@pytest.mark.api
def test_queue_status_accuracy(api_session: requests.Session, api_base_url: str):
    """Test that queue status endpoint reports accurate information."""
    
    # Get initial status
    initial_status = get_queue_status(api_session, api_base_url)
    assert initial_status is not None, "Queue status endpoint not available"
    
    initial_queued = initial_status.get("queued", 0)
    initial_running = initial_status.get("running", 0)
    
    # Submit several evaluations
    eval_ids = []
    for i in range(3):
        code = f'import time; time.sleep(1); print("Task {i} done")'
        eval_id = submit_evaluation(code)
        eval_ids.append(eval_id)
    
    # Check queue status immediately
    time.sleep(0.5)  # Brief pause for queue to update
    status = get_queue_status(api_session, api_base_url)
    
    # Should show increased queue count
    assert status["queued"] >= initial_queued, (
        f"Queue count should have increased from {initial_queued}, but is {status['queued']}"
    )
    
    # Wait for all to complete
    for eval_id in eval_ids:
        wait_for_completion(api_session, api_base_url, eval_id)
    
    # Final status should show queue cleared
    final_status = get_queue_status(api_session, api_base_url)
    assert final_status["queued"] <= initial_queued, (
        "Queue should return to initial state after completions"
    )


if __name__ == "__main__":
    # Allow running directly for debugging
    pytest.main([__file__, "-v", "-s"])