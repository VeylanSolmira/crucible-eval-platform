"""
Integration tests for priority queue functionality via the API.

These tests verify that:
1. The API accepts priority parameter for evaluations
2. High priority evaluations are processed before normal ones
3. Queue status endpoint correctly reports queue state
"""

import pytest
import requests
import time
from typing import Tuple, List, Optional


@pytest.fixture
def api_base_url() -> str:
    """Get API base URL from environment or use default."""
    import os
    return os.getenv("API_BASE_URL", "http://localhost:8000/api")


def submit_evaluation(
    api_session: requests.Session,
    api_base_url: str,
    code: str,
    priority: bool = False
) -> str:
    """Submit an evaluation with optional priority."""
    response = api_session.post(
        f"{api_base_url}/eval",
        json={"code": code, "language": "python", "priority": priority}
    )
    
    assert response.status_code == 200, f"Failed to submit evaluation: {response.text}"
    return response.json()["eval_id"]


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
def test_priority_queue_basic(api_session: requests.Session, api_base_url: str):
    """Test that high priority tasks are processed before normal tasks."""
    
    # Get initial queue status
    initial_status = get_queue_status(api_session, api_base_url)
    if initial_status:
        initial_queued = initial_status.get("queued", 0)
    else:
        initial_queued = 0
    
    # Submit evaluations
    eval_ids = []
    
    # Submit 2 normal tasks that will take time
    for i in range(2):
        code = f'import time; time.sleep(2); print("Normal task {i + 1} done")'
        eval_id = submit_evaluation(api_session, api_base_url, code, priority=False)
        eval_ids.append((eval_id, False, f"Normal {i + 1}"))
        time.sleep(0.1)
    
    # Submit high priority task (quick)
    code = 'print("HIGH PRIORITY task done!")'
    eval_id = submit_evaluation(api_session, api_base_url, code, priority=True)
    eval_ids.append((eval_id, True, "HIGH PRIORITY"))
    time.sleep(0.1)
    
    # Submit another normal task
    code = 'import time; time.sleep(2); print("Normal task 3 done")'
    eval_id = submit_evaluation(api_session, api_base_url, code, priority=False)
    eval_ids.append((eval_id, False, "Normal 3"))
    
    # Track completion order
    completion_order = []
    completed = set()
    start_time = time.time()
    
    while len(completed) < len(eval_ids) and time.time() - start_time < 30:
        for eval_id, is_priority, name in eval_ids:
            if eval_id not in completed:
                status, _ = wait_for_completion(
                    api_session, api_base_url, eval_id, timeout=0.5
                )
                if status in ["completed", "failed"]:
                    completed.add(eval_id)
                    completion_time = time.time() - start_time
                    completion_order.append((name, completion_time, status))
        time.sleep(0.1)
    
    # Verify all completed
    assert len(completed) == len(eval_ids), (
        f"Only {len(completed)} of {len(eval_ids)} evaluations completed"
    )
    
    # Verify high priority completed first
    assert completion_order[0][0] == "HIGH PRIORITY", (
        f"Expected HIGH PRIORITY to complete first, but {completion_order[0][0]} completed first. "
        f"Order: {[name for name, _, _ in completion_order]}"
    )


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
        eval_id = submit_evaluation(api_session, api_base_url, code)
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


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.slow
def test_priority_queue_stress(api_session: requests.Session, api_base_url: str):
    """Test priority queue under stress with many submissions."""
    
    # Submit many normal priority tasks
    normal_eval_ids = []
    for i in range(10):
        code = f'import time; time.sleep(0.5); print("Normal {i}")'
        eval_id = submit_evaluation(api_session, api_base_url, code, priority=False)
        normal_eval_ids.append(eval_id)
    
    # Now submit a few high priority tasks
    high_eval_ids = []
    for i in range(3):
        code = f'print("High priority {i} done quickly!")'
        eval_id = submit_evaluation(api_session, api_base_url, code, priority=True)
        high_eval_ids.append(eval_id)
    
    # Track completion times
    start_time = time.time()
    high_completion_times = []
    normal_completion_times = []
    
    # Monitor completions
    timeout = 60
    while time.time() - start_time < timeout:
        # Check high priority
        for eval_id in high_eval_ids[:]:
            status, _ = wait_for_completion(
                api_session, api_base_url, eval_id, timeout=0.1
            )
            if status in ["completed", "failed"]:
                high_completion_times.append(time.time() - start_time)
                high_eval_ids.remove(eval_id)
        
        # Check normal priority
        for eval_id in normal_eval_ids[:]:
            status, _ = wait_for_completion(
                api_session, api_base_url, eval_id, timeout=0.1
            )
            if status in ["completed", "failed"]:
                normal_completion_times.append(time.time() - start_time)
                normal_eval_ids.remove(eval_id)
        
        if not high_eval_ids and not normal_eval_ids:
            break
        
        time.sleep(0.1)
    
    # Verify all high priority completed
    assert len(high_completion_times) == 3, (
        f"Not all high priority tasks completed: {len(high_completion_times)}/3"
    )
    
    # High priority tasks should complete relatively quickly
    avg_high_time = sum(high_completion_times) / len(high_completion_times)
    assert avg_high_time < 10, (
        f"High priority tasks took too long on average: {avg_high_time:.2f}s"
    )


if __name__ == "__main__":
    # Allow running directly for debugging
    pytest.main([__file__, "-v", "-s"])