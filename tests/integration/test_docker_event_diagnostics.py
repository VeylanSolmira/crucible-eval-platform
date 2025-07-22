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
from typing import Dict, Any, List


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
        
        # Poll until completion
        poll_start = time.time()
        while time.time() - poll_start < 10:
            response = api_session.get(f"{api_base_url}/eval/{eval_id}")
            if response.status_code == 200:
                result = response.json()
                if result["status"] in ["completed", "failed", "timeout"]:
                    completion_time = time.time() - start_time
                    
                    timing_results.append({
                        "test_name": test_name,
                        "eval_id": eval_id,
                        "submission_time": submission_time,
                        "completion_time": completion_time,
                        "execution_time": completion_time - submission_time,
                        "status": result["status"],
                        "has_logs": bool(result.get("error") or result.get("output")),
                        "log_length": len(result.get("error", "") + result.get("output", ""))
                    })
                    break
            
            time.sleep(0.1)
    
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
    
    # Wait for all to complete (allowing for sequential processing)
    time.sleep(2)  # Give them time to start
    
    # TODO: Instead of waiting with a timeout, we should query the queue status
    # to know when all evaluations have been processed. This would make the test
    # more reliable and faster. See /api/queue/status endpoint.
    completion_states = {}
    max_wait = 60  # Allow more time since they may process sequentially
    check_start = time.time()
    
    while time.time() - check_start < max_wait:
        incomplete = []
        
        for eval_id in eval_ids:
            if eval_id in completion_states:
                continue
                
            response = api_session.get(f"{api_base_url}/eval/{eval_id}")
            if response.status_code == 200:
                result = response.json()
                if result["status"] in ["completed", "failed", "timeout", "cancelled"]:
                    completion_states[eval_id] = {
                        "status": result["status"],
                        "has_logs": bool(result.get("error") or result.get("output")),
                        "completion_time": time.time() - start_time
                    }
                else:
                    incomplete.append(eval_id)
        
        if not incomplete:
            break
            
        time.sleep(0.5)
    
    # Diagnostic output
    print(f"\n=== Concurrent Execution Results ===")
    print(f"Total evaluations: {len(eval_ids)}")
    print(f"Completed: {len(completion_states)}")
    print(f"Incomplete: {len(eval_ids) - len(completion_states)}")
    
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
    
    # Immediately start checking status
    checks = []
    start_time = time.time()
    
    # In Kubernetes, Celery polls every 10 seconds, so we need to wait longer
    for i in range(200):  # 20 seconds of checks (Kubernetes needs more time)
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
        
        time.sleep(0.1)
    
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