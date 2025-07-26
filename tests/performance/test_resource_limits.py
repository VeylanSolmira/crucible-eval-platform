#!/usr/bin/env python3
"""
Performance tests for resource limits and quota enforcement.

These tests verify the system handles resource constraints properly:
- ResourceQuota enforcement
- Graceful handling when limits are reached
- Proper error messages for quota exhaustion
"""

import os
import time
import pytest
import subprocess
import json
from typing import List, Dict
from tests.utils.utils import submit_evaluation, get_evaluation_status
from tests.k8s_test_config import API_URL
# from shared.utils.kubernetes_utils import get_job_name_prefix
from tests.utils.adaptive_timeouts import wait_with_progress
import requests


def get_kubernetes_jobs(namespace: str = "crucible", label_selector: str = None) -> List[Dict]:
    """Get list of Kubernetes jobs in the namespace."""
    cmd = ["kubectl", "get", "jobs", "-n", namespace, "-o", "json"]
    if label_selector:
        cmd.extend(["-l", label_selector])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.fail(f"Failed to get jobs: {result.stderr}")
    
    data = json.loads(result.stdout)
    return data.get("items", [])


@pytest.mark.kubernetes
@pytest.mark.performance
def test_resource_quota_limits():
    """Test that ResourceQuota limits are enforced for evaluation jobs."""
    print("\n" + "="*60)
    print("TEST: ResourceQuota Enforcement")
    print("="*60)
    
    # First, check if there's a ResourceQuota for evaluations
    cmd = ["kubectl", "get", "resourcequota", "-n", "crucible", "-o", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        pytest.skip("No ResourceQuota configured in namespace")
    
    quotas = json.loads(result.stdout).get("items", [])
    if not quotas:
        pytest.skip("No ResourceQuota configured in namespace")
    
    # Get current quota usage
    quota = quotas[0]  # Assume first quota applies
    quota_name = quota["metadata"]["name"]
    hard_limits = quota["status"].get("hard", {})
    used = quota["status"].get("used", {})
    
    print(f"ResourceQuota '{quota_name}':")
    print(f"  CPU limit: {used.get('requests.cpu', '0')}/{hard_limits.get('requests.cpu', 'unlimited')}")
    print(f"  Memory limit: {used.get('requests.memory', '0')}/{hard_limits.get('requests.memory', 'unlimited')}")
    print(f"  Pod limit: {used.get('pods', '0')}/{hard_limits.get('pods', 'unlimited')}")
    
    # Submit many evaluations to hit the quota
    max_pods = int(hard_limits.get('pods', '10'))
    current_pods = int(used.get('pods', '0'))
    remaining_pod_quota = max_pods - current_pods
    
    # Calculate which limit we'll hit first
    current_memory = used.get('requests.memory', '0')
    max_memory = hard_limits.get('requests.memory', '4Gi')
    # Convert memory strings to Mi for calculation
    current_memory_mi = int(current_memory.rstrip('Mi')) if current_memory.endswith('Mi') else 0
    max_memory_mi = int(max_memory.rstrip('Mi')) if max_memory.endswith('Mi') else 4096
    remaining_memory_quota = max_memory_mi - current_memory_mi
    
    # With 24Mi per pod, how many can we fit?
    pods_that_fit_memory = remaining_memory_quota // 24
    
    print(f"\nQuota analysis:")
    print(f"  Remaining pod quota: {remaining_pod_quota}")
    print(f"  Pods that fit in memory (24Mi each): {pods_that_fit_memory}")
    
    # We'll likely hit memory limit first unless we use tiny pods
    num_evaluations = min(min(remaining_pod_quota, pods_that_fit_memory) + 5, 20)  # Try to exceed quota by 5, cap at 20
    
    print(f"\nSubmitting {num_evaluations} evaluations to test quota limits...")
    eval_ids = []
    quota_hit = False
    
    for i in range(num_evaluations):
        try:
            eval_id = submit_evaluation(
                f'print("Q{i}")',  # Minimal code to reduce memory usage
                cpu_limit="50m",   # Minimal CPU
                memory_limit="24Mi",  # Minimum viable memory for Python
                timeout=10,  # Shorter timeout for faster testing
                executor_image="executor-base"  # Use minimal executor for smaller memory footprint
            )
            if eval_id:
                eval_ids.append(eval_id)
                print(f"  {i+1}: Submitted {eval_id}")
            else:
                print(f"  {i+1}: Failed to submit (quota reached?)")
                quota_hit = True
                break
        except Exception as e:
            print(f"  {i+1}: Error: {e}")
            if "exceeded quota" in str(e).lower() or "forbidden" in str(e).lower():
                quota_hit = True
                break
    
    # We should either hit quota or submit exactly what we expected
    expected_successful = min(remaining_pod_quota, pods_that_fit_memory)
    assert quota_hit or len(eval_ids) == min(expected_successful, num_evaluations), \
        f"Should have hit quota limits or submitted exactly {min(expected_successful, num_evaluations)} jobs, but only submitted {len(eval_ids)}"
    
    # Clean up: wait for some completions or cancel jobs
    print("\nCleaning up test jobs...")
    jobs = get_kubernetes_jobs("crucible", "app=evaluation")
    for job in jobs[:5]:  # Clean up first 5 jobs
        job_name = job["metadata"]["name"]
        subprocess.run(
            ["kubectl", "delete", "job", job_name, "-n", "crucible", "--wait=false"],
            capture_output=True
        )
    
    print(f"✅ ResourceQuota enforcement verified")


@pytest.mark.kubernetes
@pytest.mark.performance
@pytest.mark.skip(reason="Future feature: API-level resource validation")
def test_api_resource_validation():
    """Test that API rejects excessive resource requests immediately."""
    print("\n" + "="*60)
    print("TEST: API Resource Validation")
    print("="*60)
    
    # This test is for future API-level validation
    # Currently, validation happens asynchronously in the dispatcher
    
    response = requests.post(
        f"{API_URL}/eval",
        json={
            "code": 'print("Excessive resource test")',
            "language": "python",
            "timeout": 10,
            "cpu_limit": "100",  # 100 CPUs - should exceed any reasonable quota
            "memory_limit": "1000Gi"  # 1TB - should exceed quota
        }
    )
    
    # Future: API should reject with 400
    assert response.status_code == 400
    error = response.json().get("detail", "")
    assert "exceeds" in error.lower()
    print(f"✅ Got expected API rejection: {error}")


@pytest.mark.kubernetes
@pytest.mark.performance
def test_quota_error_handling():
    """Test that quota exhaustion provides clear error messages."""
    print("\n" + "="*60)
    print("TEST: Quota Exhaustion Error Handling")
    print("="*60)
    
    # Check if ResourceQuota exists
    cmd = ["kubectl", "get", "resourcequota", "-n", "crucible", "-o", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0 or not json.loads(result.stdout).get("items"):
        pytest.skip("No ResourceQuota configured in namespace")
    
    # Submit a job with excessive resource requests
    print("Submitting job with excessive resources (100 CPUs, 1TB memory)...")
    
    # Submit the evaluation - API should reject it immediately
    response = requests.post(
        f"{API_URL}/eval",
        json={
            "code": 'print("Excessive resource test")',
            "language": "python",
            "timeout": 10,
            "cpu_limit": "100",  # 100 CPUs - should exceed any reasonable quota
            "memory_limit": "1000Gi"  # 1TB - should exceed quota
        }
    )
    
    # API should reject with 400 due to resource validation
    if response.status_code == 400:
        error_detail = response.json().get("detail", "")
        error_lower = error_detail.lower()
        
        # Check for expected error message
        assert any(phrase in error_lower for phrase in [
            "exceeds total cluster limit",
            "exceeds cluster",
            "requested memory",
            "requested cpu",
            "1000gi",
            "100"
        ]), f"Expected resource limit error, got: {error_detail}"
        
        print(f"✅ Got expected resource limit error: {error_detail}")
    else:
        # If API accepted it (shouldn't happen with new validation), 
        # fall back to checking async validation
        assert response.status_code in [200, 202], f"Expected 400 or successful submission, got {response.status_code}"
        eval_id = response.json().get("eval_id")
        assert eval_id is not None, "No eval_id in response"
        
        pytest.fail(f"Expected API to reject excessive resources with 400, but got {response.status_code}")


def get_job_count(namespace: str = "crucible", label_selector: str = None) -> int:
    """Get count of Kubernetes jobs."""
    jobs = get_kubernetes_jobs(namespace, label_selector)
    return len(jobs)


@pytest.mark.kubernetes
@pytest.mark.performance  
def test_high_throughput_job_handling():
    """Test system can handle high throughput of Kubernetes Jobs."""
    print("\n" + "="*60)
    print("TEST: High Throughput Job Handling")
    print("="*60)
    
    # Get initial metrics
    initial_job_count = get_job_count("crucible", "app=evaluation")
    
    # Submit many short evaluations
    batch_size = 20
    eval_ids = []
    
    print(f"Submitting {batch_size} evaluations...")
    start_time = time.time()
    
    for i in range(batch_size):
        code = f'print("High throughput test {i}: " + str({i} * {i}))'
        eval_id = submit_evaluation(
            code,
            cpu_limit="50m",      # Minimal CPU for throughput testing
            memory_limit="128Mi", # Reduced memory for throughput testing
            timeout=10,           # Shorter timeout for faster completion
            executor_image="executor-base"  # Use minimal executor for consistency
        )
        if eval_id:
            eval_ids.append(eval_id)
        
        # Progress indicator
        if (i + 1) % 5 == 0:
            print(f"  Submitted {i + 1}/{batch_size}")
    
    submission_time = time.time() - start_time
    assert len(eval_ids) >= batch_size * 0.9, f"Failed to submit enough evaluations"
    
    print(f"\n📊 Submission metrics:")
    print(f"  Submitted: {len(eval_ids)} evaluations")
    print(f"  Time taken: {submission_time:.1f}s")
    print(f"  Rate: {len(eval_ids)/submission_time:.1f} submissions/second")
    
    # Use adaptive waiter for monitoring completion
    print("\nMonitoring completion with adaptive timeout...")
    
    # First, let's check if evaluations are even being processed
    print("\nChecking evaluation statuses after submission...")
    time.sleep(5)  # Give system time to process
    
    sample_statuses = {}
    for i, eval_id in enumerate(eval_ids[:5]):  # Check first 5
        status = get_evaluation_status(eval_id)
        sample_statuses[eval_id[-8:]] = status.get("status", "unknown")
    
    print(f"Sample evaluation statuses: {sample_statuses}")
    
    # Check if there are any jobs in the namespace
    jobs = get_kubernetes_jobs("crucible", "app=evaluation")
    print(f"Total evaluation jobs in namespace: {len(jobs)}")
    if jobs:
        recent_jobs = [j for j in jobs if any(eval_id[:8] in j["metadata"]["name"] for eval_id in eval_ids)]
        print(f"Jobs from this test run: {len(recent_jobs)}")
    
    # Create a session for the API
    api_session = requests.Session()
    
    # Wait with adaptive timeout
    results = wait_with_progress(
        api_session, 
        API_URL,
        eval_ids,
        timeout=180.0,  # Base timeout
        check_resources=True
    )
    
    completed = len(results["completed"])
    failed = len(results["failed"])
    completion_time = results["duration"]
    
    # Final metrics
    print(f"\n📊 Completion metrics:")
    print(f"  Completed: {completed}/{len(eval_ids)}")
    print(f"  Failed: {failed}")
    print(f"  Time taken: {completion_time:.1f}s")
    print(f"  Throughput: {completed/completion_time:.2f} completions/second")
    
    # Assertions - all submitted evaluations should complete
    assert completed == len(eval_ids), f"Not all evaluations completed: only {completed}/{len(eval_ids)} completed"
    assert completion_time < 120, f"Took too long: {completion_time}s"
    
    # Check job cleanup
    print("\nChecking job cleanup...")
    current_job_count = get_job_count("crucible", "app=evaluation")
    print(f"Current evaluation jobs: {current_job_count} (initial: {initial_job_count})")
    
    # Jobs should be cleaned up by TTL controller
    if current_job_count > initial_job_count + 5:
        print("⚠️  Many jobs still present - TTL controller may be slow")
    else:
        print("✅ Job cleanup is working")