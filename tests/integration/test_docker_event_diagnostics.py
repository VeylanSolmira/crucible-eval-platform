"""
Diagnostic tests for Docker event handling and log retrieval.

These tests help diagnose issues with the Docker event system and verify
that the executor service properly handles container lifecycle events.

NOTE: In Kubernetes, these tests have different characteristics:
- No Docker events - Kubernetes uses Job status instead
- Celery polls every 10 seconds instead of instant Docker events  
- Container removal timing is not an issue (Jobs persist)
- These tests might be better suited as unit tests for the Celery worker
"""

import pytest
import time
import requests
import json
from typing import Dict, Any, List, Optional


def wait_for_evaluation_completion(
    api_session: requests.Session,
    api_base_url: str,
    eval_id: str,
    timeout: float = 30.0,
    initial_delay: float = 0.1,
    max_delay: float = 2.0,
    backoff_factor: float = 1.5
) -> Optional[Dict[str, Any]]:
    """
    Wait for evaluation completion using exponential backoff.
    
    With event-based messaging, evaluations complete faster, so we start
    with a short delay and increase it exponentially to reduce polling.
    
    Returns the final evaluation result or None if timeout.
    """
    start_time = time.time()
    delay = initial_delay
    
    while time.time() - start_time < timeout:
        response = api_session.get(f"{api_base_url}/eval/{eval_id}")
        if response.status_code == 200:
            result = response.json()
            if result["status"] in ["completed", "failed", "timeout", "cancelled"]:
                return result
        
        # Exponential backoff with max delay
        time.sleep(delay)
        delay = min(delay * backoff_factor, max_delay)
    
    return None


def get_executor_status(api_session: requests.Session, api_base_url: str) -> Dict[str, Any]:
    """Get the status of all executor services."""
    # Note: This assumes an executor status endpoint exists
    # If not, this test can be skipped
    try:
        response = api_session.get(f"{api_base_url.replace('/api', '')}/executor/status")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {}


def submit_evaluation_batch(
    api_session: requests.Session, 
    api_base_url: str,
    codes: List[str],
    timeout: int = 30
) -> List[str]:
    """Submit multiple evaluations and return their IDs."""
    eval_ids = []
    
    for code in codes:
        response = api_session.post(
            f"{api_base_url}/eval",
            json={
                "code": code,
                "language": "python",
                "timeout": timeout
            }
        )
        if response.status_code == 200:
            eval_ids.append(response.json()["eval_id"])
        else:
            raise RuntimeError(f"Failed to submit evaluation: {response.text}")
    
    return eval_ids


@pytest.mark.whitebox
@pytest.mark.integration
@pytest.mark.api
def test_diagnose_container_lifecycle_timing(api_session: requests.Session, api_base_url: str):
    """
    Diagnostic test to measure container lifecycle timing.
    
    This helps identify how quickly containers are failing and whether
    the event system has enough time to capture logs.
    """
    timing_results = []
    
    test_codes = [
        # Instant failure
        ("instant_error", "1/0"),
        # Failure after print
        ("print_then_error", 'print("Output before error"); 1/0'),
        # Failure with sleep
        ("sleep_then_error", 'import time; time.sleep(0.5); print("After sleep"); 1/0'),
        # Normal completion
        ("normal_completion", 'print("Success")'),
    ]
    
    for test_name, code in test_codes:
        start_time = time.time()
        
        # Submit evaluation
        response = api_session.post(
            f"{api_base_url}/eval",
            json={
                "code": code,
                "language": "python",
                "timeout": 30
            }
        )
        
        assert response.status_code == 200
        eval_id = response.json()["eval_id"]
        submission_time = time.time() - start_time
        
        # Wait for completion with exponential backoff
        result = wait_for_evaluation_completion(
            api_session, api_base_url, eval_id, 
            timeout=30.0,  # Increased timeout for Kubernetes job scheduling
            initial_delay=0.05  # Start with 50ms for fast completions
        )
        
        if result:
            completion_time = time.time() - start_time
            
            timing_results.append({
                "test_name": test_name,
                "eval_id": eval_id,
                "submission_time": submission_time,
                "completion_time": completion_time,
                "execution_time": completion_time - submission_time,
                "status": result["status"],
                "has_logs": bool(result.get("error") or result.get("output")),
                "log_length": len((result.get("error") or "") + (result.get("output") or ""))
            })
        else:
            pytest.fail(f"Evaluation {eval_id} for test '{test_name}' timed out")
    
    # Diagnostic output
    print("\n=== Container Lifecycle Timing Results ===")
    for result in timing_results:
        print(f"\nTest: {result['test_name']}")
        print(f"  Submission time: {result['submission_time']:.3f}s")
        print(f"  Total time: {result['completion_time']:.3f}s")
        print(f"  Execution time: {result['execution_time']:.3f}s")
        print(f"  Status: {result['status']}")
        print(f"  Has logs: {result['has_logs']} (length: {result['log_length']})")
    
    # Verify all fast-failing containers have logs
    for result in timing_results:
        if result["test_name"] != "normal_completion" and not result["has_logs"]:
            pytest.fail(
                f"Fast-failing test '{result['test_name']}' has no logs! "
                f"Execution time was {result['execution_time']:.3f}s"
            )


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.slow
def test_concurrent_fast_failures_event_handling(api_session: requests.Session, api_base_url: str):
    """
    Test that concurrent fast-failing containers don't overwhelm the event system.
    
    This simulates the race condition scenario where multiple containers die
    almost simultaneously.
    """
    # Submit 10 fast-failing evaluations as quickly as possible
    codes = [f'print("Concurrent test {i}"); 1/{i}' for i in range(10)]
    
    start_time = time.time()
    eval_ids = submit_evaluation_batch(api_session, api_base_url, codes)
    submission_time = time.time() - start_time
    
    print(f"\nSubmitted {len(eval_ids)} evaluations in {submission_time:.3f}s")
    
    # Wait for all to complete in parallel with shorter timeouts
    completion_states = {}
    remaining_evals = set(eval_ids)
    
    # Poll all evaluations in parallel with event-aware timing
    overall_timeout = 30.0  # 30s should be plenty for simple failures
    deadline = time.time() + overall_timeout
    poll_interval = 0.2  # Start with 200ms polls
    max_poll_interval = 2.0
    
    while remaining_evals and time.time() < deadline:
        # Check all remaining evaluations in a single batch
        for eval_id in list(remaining_evals):
            try:
                response = api_session.get(f"{api_base_url}/eval/{eval_id}")
                if response.status_code == 200:
                    result = response.json()
                    if result["status"] in ["completed", "failed", "timeout", "cancelled"]:
                        completion_states[eval_id] = {
                            "status": result["status"],
                            "has_logs": bool(result.get("error") or result.get("output")),
                            "completion_time": time.time() - start_time
                        }
                        remaining_evals.remove(eval_id)
            except Exception as e:
                print(f"Error checking {eval_id}: {e}")
        
        if remaining_evals:
            time.sleep(poll_interval)
            # Exponential backoff up to max
            poll_interval = min(poll_interval * 1.5, max_poll_interval)
    
    # Diagnostic output
    total_time = time.time() - start_time
    print(f"\n=== Concurrent Execution Results ===")
    print(f"Total evaluations: {len(eval_ids)}")
    print(f"Completed: {len(completion_states)}")
    print(f"Incomplete: {len(eval_ids) - len(completion_states)}")
    print(f"Total test time: {total_time:.3f}s")
    
    if completion_states:
        completion_times = [state["completion_time"] for state in completion_states.values()]
        print(f"First completion: {min(completion_times):.3f}s")
        print(f"Last completion: {max(completion_times):.3f}s")
        print(f"Average completion: {sum(completion_times)/len(completion_times):.3f}s")
    
    # Check for issues
    stuck_evals = [eid for eid in eval_ids if eid not in completion_states]
    no_log_evals = [
        eid for eid, state in completion_states.items() 
        if not state["has_logs"]
    ]
    
    if stuck_evals:
        pytest.fail(
            f"{len(stuck_evals)} evaluations got stuck! IDs: {stuck_evals[:5]}... "
            "This indicates the event handler may be dropping events under load."
        )
    
    if no_log_evals:
        pytest.fail(
            f"{len(no_log_evals)} evaluations completed without logs! "
            "This suggests the log retrieval race condition still exists."
        )


@pytest.mark.integration
@pytest.mark.api
def test_container_removal_timing(api_session: requests.Session, api_base_url: str):
    """
    Test to verify that containers aren't removed too quickly.
    
    This helps diagnose if the "container not found" errors are due to
    premature cleanup.
    """
    # Submit evaluation that prints and then fails
    code = '''
import sys
print("Starting execution", flush=True)
sys.stderr.write("Error stream test\\n")
sys.stderr.flush()
print("About to fail", flush=True)
raise ValueError("Test error with details")
'''
    
    response = api_session.post(
        f"{api_base_url}/eval",
        json={
            "code": code,
            "language": "python",
            "timeout": 30
        }
    )
    
    assert response.status_code == 200
    eval_id = response.json()["eval_id"]
    
    # Track status progression with exponential backoff
    checks = []
    start_time = time.time()
    delay = 0.05
    
    while time.time() - start_time < 20:  # 20 second timeout
        response = api_session.get(f"{api_base_url}/eval/{eval_id}")
        check_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            checks.append({
                "time": check_time,
                "status": result["status"],
                "has_output": bool(result.get("output")),
                "has_error": bool(result.get("error")),
                "runtime_ms": result.get("runtime_ms", 0)
            })
            
            if result["status"] in ["completed", "failed"]:
                break
        
        time.sleep(delay)
        delay = min(delay * 1.5, 2.0)  # Exponential backoff
    
    # Analyze the progression
    print(f"\n=== Container Lifecycle Progression ===")
    for check in checks:
        print(f"  {check['time']:.3f}s: status={check['status']}, "
              f"output={check['has_output']}, error={check['has_error']}, "
              f"runtime={check['runtime_ms']}ms")
    
    # Verify we got logs in the final state
    final_check = checks[-1] if checks else {}
    assert final_check.get("has_error") or final_check.get("has_output"), (
        "No logs captured in final state! Container may have been removed too quickly."
    )


if __name__ == "__main__":
    # Allow running directly for debugging
    pytest.main([__file__, "-v", "-s"])