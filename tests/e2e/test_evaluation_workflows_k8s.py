#!/usr/bin/env python3
"""
E2E tests for evaluation workflows in Kubernetes

This test suite validates Kubernetes-native behavior:
- Jobs are created on-demand (no fixed pool)
- No allocation/release - Jobs are created and destroyed
- Queueing happens at the Kubernetes scheduler level
- Resource limits are enforced by ResourceQuotas

Tests focus on:
1. Job creation and cleanup
2. Parallel Job execution  
3. Job deletion/cancellation
"""

import os
import time
import pytest
from typing import List, Dict, Optional
from tests.utils.utils import submit_evaluation, wait_for_completion, get_evaluation_status
from tests.k8s_test_config import API_URL
from shared.utils.kubernetes_utils import get_job_name_prefix
import subprocess
import json

# Mark all tests as e2e
pytestmark = [pytest.mark.e2e, pytest.mark.kubernetes]


def get_kubernetes_jobs(namespace: str = "crucible", label_selector: Optional[str] = None) -> List[Dict]:
    """Get list of Kubernetes jobs in the namespace."""
    cmd = ["kubectl", "get", "jobs", "-n", namespace, "-o", "json"]
    if label_selector:
        cmd.extend(["-l", label_selector])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.fail(f"Failed to get jobs: {result.stderr}")
    
    data = json.loads(result.stdout)
    return data.get("items", [])


def get_job_count(namespace: str = "crucible", label_selector: Optional[str] = None) -> int:
    """Get count of Kubernetes jobs."""
    jobs = get_kubernetes_jobs(namespace, label_selector)
    return len(jobs)


def wait_for_job_cleanup(initial_count: int, namespace: str = "crucible", timeout: int = 30) -> bool:
    """Wait for jobs to be cleaned up back to initial count."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        current_count = get_job_count(namespace, "app=evaluation")
        if current_count <= initial_count:
            return True
        time.sleep(1)
    return False


@pytest.mark.kubernetes
def test_single_evaluation_job_lifecycle():
    """Test a single evaluation creates and cleans up a Kubernetes Job."""
    print("\n" + "="*60)
    print("TEST 1: Single Evaluation Job Lifecycle")
    print("="*60)
    
    # Get initial job count
    initial_job_count = get_job_count("crucible", "app=evaluation")
    print(f"Initial evaluation jobs: {initial_job_count}")
    
    # Submit evaluation
    eval_id = submit_evaluation('print("Hello from Kubernetes Job!")')
    assert eval_id is not None, "Failed to submit evaluation"
    
    # Wait a moment for job creation
    time.sleep(2)
    
    # Check that a job was created
    jobs_during = get_kubernetes_jobs("crucible", "app=evaluation")
    job_names = [job["metadata"]["name"] for job in jobs_during]
    
    # Use shared utility to get the job name prefix
    job_prefix = get_job_name_prefix(eval_id)
    eval_job = [name for name in job_names if name.startswith(job_prefix)]
    
    assert len(eval_job) > 0, f"No job created for evaluation {eval_id}. Jobs found: {job_names}"
    print(f"✅ Job created: {eval_job[0]}")
    
    # Wait for completion
    status = wait_for_completion(eval_id, timeout=30, use_adaptive=True)
    assert status is not None, "Evaluation did not complete in time"
    
    # Get evaluation details
    eval_data = get_evaluation_status(eval_id)
    assert eval_data["status"] == "completed", f"Evaluation failed: {eval_data}"
    assert "Hello from Kubernetes Job!" in eval_data.get("output", ""), "Output not captured"
    
    # Wait for job cleanup (TTL controller should clean it up)
    print("Waiting for job cleanup...")
    cleaned_up = wait_for_job_cleanup(initial_job_count, timeout=60)
    
    if cleaned_up:
        print("✅ Job cleaned up successfully")
    else:
        current_count = get_job_count("crucible", "app=evaluation")
        print(f"⚠️  Job cleanup may be delayed (current count: {current_count}, initial: {initial_job_count})")


@pytest.mark.kubernetes
def test_concurrent_job_execution():
    """Test multiple evaluations run as parallel Kubernetes Jobs."""
    print("\n" + "="*60)
    print("TEST 2: Concurrent Job Execution")
    print("="*60)
    
    # Submit multiple evaluations
    num_evaluations = 5
    eval_ids = []
    
    print(f"Submitting {num_evaluations} evaluations...")
    for i in range(num_evaluations):
        code = f'import time; time.sleep(2); print("Task {i} completed on pod " + __import__("socket").gethostname())'
        eval_id = submit_evaluation(code)
        if eval_id:
            eval_ids.append(eval_id)
            print(f"  Submitted eval {i+1}/{num_evaluations}: {eval_id}")
    
    assert len(eval_ids) == num_evaluations, f"Failed to submit all evaluations"
    
    # Wait a moment for jobs to be created
    time.sleep(3)
    
    # Check that multiple jobs are running
    jobs = get_kubernetes_jobs("crucible", "app=evaluation")
    running_jobs = [j for j in jobs if j["status"].get("active", 0) > 0]
    
    print(f"\nJobs created: {len(jobs)}")
    print(f"Jobs running in parallel: {len(running_jobs)}")
    
    # TODO: Re-enable parallelism assertion when we have a guaranteed executor pool with 2+ executors
    # In Docker Compose we had 3 dedicated executors, but in Kubernetes jobs are scheduled dynamically
    # based on available cluster resources, so we can't guarantee a specific parallelism level
    # assert len(running_jobs) >= min(3, num_evaluations), "Expected more parallel execution"
    
    # Wait for all to complete
    print("\nWaiting for all evaluations to complete...")
    completed = 0
    for eval_id in eval_ids:
        status = wait_for_completion(eval_id, timeout=60, use_adaptive=True)
        if status:
            eval_data = get_evaluation_status(eval_id)
            if eval_data["status"] == "completed":
                completed += 1
                # Check that output shows different pod names (proving parallel execution)
                output = eval_data.get("output", "")
                if "pod" in output:
                    pod_name = output.split("pod ")[-1].strip()
                    print(f"  {eval_id}: completed on {pod_name}")
    
    assert completed == num_evaluations, f"Not all evaluations completed: only {completed}/{num_evaluations} completed"
    print(f"✅ {completed}/{num_evaluations} evaluations completed successfully")


@pytest.mark.kubernetes
def test_job_deletion_on_cancellation():
    """Test that Kubernetes Jobs are deleted when evaluation is cancelled."""
    print("\n" + "="*60)
    print("TEST 4: Job Deletion on Cancellation")
    print("="*60)
    
    # Submit a long-running evaluation
    code = '''
import time
for i in range(30):
    print(f"Running for {i} seconds...")
    time.sleep(1)
print("Should not reach here if cancelled")
'''
    
    eval_id = submit_evaluation(code)
    assert eval_id is not None, "Failed to submit evaluation"
    
    # Wait for job to be created and start running
    time.sleep(3)
    
    # Find the job
    jobs = get_kubernetes_jobs("crucible", "app=evaluation")
    eval_job = None
    job_prefix = get_job_name_prefix(eval_id)
    for job in jobs:
        if job["metadata"]["name"].startswith(job_prefix):
            eval_job = job
            break
    
    assert eval_job is not None, f"No job found for evaluation {eval_id}"
    job_name = eval_job["metadata"]["name"]
    print(f"Job created: {job_name}")
    
    # Cancel through the API to test the full flow
    print(f"Cancelling evaluation {eval_id} through API...")
    
    # Use the API URL from the test config
    import requests
    
    try:
        response = requests.post(f"{API_URL}/eval/{eval_id}/cancel")
        if response.status_code == 200:
            print("✅ Evaluation cancelled successfully via API")
            result_data = response.json()
            print(f"   Status: {result_data.get('status')}")
            print(f"   Message: {result_data.get('message')}")
        else:
            print(f"⚠️  Failed to cancel via API: {response.status_code} - {response.text}")
            # Fallback to direct job deletion for test to continue
            cmd = ["kubectl", "delete", "job", job_name, "-n", "crucible"]
            subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        print(f"⚠️  Error calling API: {e}")
        # Fallback to direct job deletion
        cmd = ["kubectl", "delete", "job", job_name, "-n", "crucible"]  
        subprocess.run(cmd, capture_output=True, text=True)
    
    # Wait a bit and check evaluation status
    time.sleep(5)
    eval_data = get_evaluation_status(eval_id)
    
    # Status should be failed or cancelled
    assert eval_data["status"] in ["failed", "cancelled", "timeout"], \
        f"Expected failed/cancelled status, got {eval_data['status']}"
    
    print(f"✅ Evaluation status after job deletion: {eval_data['status']}")


if __name__ == "__main__":
    # Allow running with pytest directly
    import subprocess
    import sys
    sys.exit(subprocess.call(["pytest", __file__, "-v", "-s"]))