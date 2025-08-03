"""
End-to-end tests for priority queue functionality.

These tests verify the complete evaluation execution flow with priority handling,
from submission through completion. They require the full system to be operational
including evaluation execution.

NOTE: These tests are currently SKIPPED because Redis does not support true priority
queues. With Redis, Celery checks queues in round-robin fashion, providing only
partial prioritization (~50% preference for high-priority tasks).

For true priority queue support, we would need to migrate to RabbitMQ.
See: docs/architecture/celery-redis-vs-rabbitmq.md

When/if we migrate to RabbitMQ, these tests should be re-enabled and will pass.
"""

import pytest
import requests
import time
from typing import Tuple, List, Optional
from tests.k8s_test_config import API_URL
from tests.utils.utils import submit_evaluation
from shared.constants.evaluation_defaults import PriorityClass


def wait_for_completion(
    eval_id: str,
    timeout: float = 30
) -> Tuple[str, float]:
    """Wait for evaluation to complete and return (status, duration)."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = requests.get(f"{API_URL}/eval/{eval_id}")
        if response.status_code == 200:
            result = response.json()
            status = result.get("status", "unknown")
            if status in ["completed", "failed", "timeout", "cancelled"]:
                duration = time.time() - start_time
                return status, duration
        time.sleep(0.2)
    
    return "timeout", timeout


@pytest.mark.e2e
@pytest.mark.whitebox
@pytest.mark.skip(reason="Redis doesn't support true priority queues. See docs/architecture/celery-redis-vs-rabbitmq.md")
def test_priority_queue_execution_order():
    """Test that high priority tasks are executed before normal tasks when queue is full."""
    
    # Get actual running Celery workers from the cluster
    import subprocess
    import json
    
    # Get actual running celery-worker pods (not just deployment spec)
    result = subprocess.run(
        ["kubectl", "get", "pods", "-n", "crucible", "-l", "app=celery-worker", 
         "--field-selector=status.phase=Running", "-o", "json"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        # If kubectl fails, fall back to deployment manifest
        print(f"Warning: Failed to get celery-worker pods: {result.stderr}")
        print("Falling back to deployment manifest...")
        
        # Query the deployment spec
        deployment_result = subprocess.run(
            ["kubectl", "get", "deployment", "celery-worker", "-n", "crucible", "-o", "json"],
            capture_output=True,
            text=True
        )
        
        if deployment_result.returncode == 0:
            deployment_info = json.loads(deployment_result.stdout)
            num_workers = deployment_info["spec"].get("replicas", 2)
            
            # Extract concurrency from deployment env vars
            concurrency_per_worker = 2  # Default
            containers = deployment_info["spec"]["template"]["spec"]["containers"]
            for container in containers:
                if container["name"] == "celery-worker":
                    for env in container.get("env", []):
                        if env["name"] == "CELERY_CONCURRENCY":
                            concurrency_per_worker = int(env["value"])
                            break
                    break
            print(f"Using deployment spec: {num_workers} workers with concurrency {concurrency_per_worker}")
        else:
            # Final fallback if both queries fail
            print(f"Failed to get deployment spec: {deployment_result.stderr}")
            pytest.skip("Cannot determine Celery worker configuration from cluster")
    else:
        pods_info = json.loads(result.stdout)
        running_pods = pods_info.get("items", [])
        num_workers = len(running_pods)
        
        # Get concurrency from first pod's env vars
        concurrency_per_worker = 2  # Default
        if running_pods:
            pod = running_pods[0]
            containers = pod["spec"]["containers"]
            for container in containers:
                if container["name"] == "celery-worker":
                    for env in container.get("env", []):
                        if env["name"] == "CELERY_CONCURRENCY":
                            concurrency_per_worker = int(env["value"])
                            break
                    break
    
    total_slots = num_workers * concurrency_per_worker
    print(f"Found {num_workers} running workers with concurrency {concurrency_per_worker} = {total_slots} total slots")
    
    # Step 1: Fill all worker slots with long-running tasks
    print(f"Filling {total_slots} worker slots with blocking tasks...")
    blocker_ids = []
    for i in range(total_slots):
        # Use 30s sleep to ensure tasks stay running through multiple poll cycles
        code = f'import time; time.sleep(30); print("Blocker {i} done")'
        eval_id = submit_evaluation(code, priority=PriorityClass.TEST_LOW_PRIORITY_EVAL)
        blocker_ids.append(eval_id)
    
    # Step 2: Wait for all blockers to be in "running" state
    print("Waiting for all blockers to start running...")
    for i in range(30):  # Max 30 seconds to wait
        running_count = 0
        for eval_id in blocker_ids:
            response = requests.get(f"{API_URL}/eval/{eval_id}")
            if response.status_code == 200 and response.json()["status"] == "running":
                running_count += 1
        
        if running_count == total_slots:
            print(f"All {total_slots} blockers are running")
            break
        
        print(f"Waiting... {running_count}/{total_slots} blockers running")
        time.sleep(2)
    else:
        pytest.fail(f"Only {running_count}/{total_slots} blockers started running after 30s")
    
    # Step 3: Submit tasks that will be queued
    print("Submitting queued tasks...")
    queued_eval_ids = []
    
    # Submit normal priority tasks first
    for i in range(3):
        code = f'print("Queued normal task {i} completed")'
        eval_id = submit_evaluation(code, priority=PriorityClass.TEST_LOW_PRIORITY_EVAL)
        queued_eval_ids.append((eval_id, False, f"Normal {i}"))
    
    # Submit high priority task
    code = 'print("HIGH PRIORITY task completed!")'
    high_priority_id = submit_evaluation(code, priority=PriorityClass.TEST_NORMAL_PRIORITY_EVAL)
    queued_eval_ids.append((high_priority_id, True, "HIGH PRIORITY"))
    
    # Step 4: Cancel one blocker to free up a slot
    print("Cancelling one blocker to free a worker slot...")
    cancel_response = requests.post(f"{API_URL}/eval/{blocker_ids[0]}/cancel")
    assert cancel_response.status_code == 200, "Failed to cancel blocker"
    
    # Step 5: Wait to see which queued task completes first
    print("Waiting to see which queued task gets picked up...")
    first_completed = None
    start_time = time.time()
    
    while time.time() - start_time < 60:
        for eval_id, is_priority, name in queued_eval_ids:
            response = requests.get(f"{API_URL}/eval/{eval_id}")
            if response.status_code == 200:
                status = response.json()["status"]
                if status in ["completed", "failed"]:
                    first_completed = name
                    break
        if first_completed:
            break
        time.sleep(0.5)
    
    # Cleanup: Cancel remaining tasks
    print("Cleaning up remaining tasks...")
    for eval_id in blocker_ids[1:]:
        try:
            requests.post(f"{API_URL}/eval/{eval_id}/cancel")
        except:
            pass
    
    # Verify high priority completed first
    assert first_completed == "HIGH PRIORITY", (
        f"Expected HIGH PRIORITY to complete first, but {first_completed} completed first. "
        "This indicates priority queue is not working correctly."
    )


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.skip(reason="Redis doesn't support true priority queues. See docs/architecture/celery-redis-vs-rabbitmq.md")
def test_priority_queue_under_load():
    """Test priority queue behavior under load with many submissions."""
    
    # Submit many normal priority tasks
    normal_eval_ids = []
    for i in range(10):
        code = f'import time; time.sleep(0.5); print("Normal {i}")'
        eval_id = submit_evaluation(code, priority=PriorityClass.TEST_LOW_PRIORITY_EVAL)
        normal_eval_ids.append(eval_id)
    
    # Now submit a few high priority tasks
    high_eval_ids = []
    for i in range(3):
        code = f'print("High priority {i} done quickly!")'
        eval_id = submit_evaluation(code, priority=PriorityClass.TEST_NORMAL_PRIORITY_EVAL)
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
                eval_id, timeout=0.1
            )
            if status in ["completed", "failed"]:
                high_completion_times.append(time.time() - start_time)
                high_eval_ids.remove(eval_id)
        
        # Check normal priority
        for eval_id in normal_eval_ids[:]:
            status, _ = wait_for_completion(
                eval_id, timeout=0.1
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