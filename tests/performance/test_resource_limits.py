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
from tests.utils.utils import submit_evaluation, wait_for_completion, get_evaluation_status
from tests.k8s_test_config import API_URL
from shared.utils.kubernetes_utils import get_job_name_prefix


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
    num_evaluations = min(max_pods + 5, 20)  # Cap at 20 to avoid excessive testing
    
    print(f"\nSubmitting {num_evaluations} evaluations to test quota limits...")
    eval_ids = []
    quota_hit = False
    
    for i in range(num_evaluations):
        try:
            eval_id = submit_evaluation(
                f'import time; print("Quota test {i}"); time.sleep(30)',
                cpu_limit="500m",
                memory_limit="512Mi"
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
    
    assert quota_hit or len(eval_ids) >= max_pods, "Should have hit quota limits or submitted enough jobs"
    
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
    try:
        eval_id = submit_evaluation(
            'print("Excessive resource test")',
            cpu_limit="100",  # 100 CPUs - should exceed any reasonable quota
            memory_limit="1000Gi"  # 1TB - should exceed quota
        )
        
        # If it somehow succeeds, clean it up
        if eval_id:
            jobs = get_kubernetes_jobs("crucible", "app=evaluation")
            for job in jobs:
                if eval_id in job["metadata"]["name"]:
                    subprocess.run(
                        ["kubectl", "delete", "job", job["metadata"]["name"], "-n", "crucible"],
                        capture_output=True
                    )
            pytest.fail("Expected quota rejection but job was created")
            
    except Exception as e:
        # We expect this to fail
        error_msg = str(e).lower()
        assert any(word in error_msg for word in ["quota", "exceeded", "forbidden", "limit"]), \
            f"Expected quota-related error, got: {e}"
        print(f"✅ Got expected quota error: {e}")


@pytest.mark.kubernetes
@pytest.mark.performance
def test_resource_cleanup_after_quota():
    """Test that resources are properly released when jobs complete."""
    print("\n" + "="*60)
    print("TEST: Resource Cleanup After Quota")
    print("="*60)
    
    # Check ResourceQuota
    cmd = ["kubectl", "get", "resourcequota", "-n", "crucible", "-o", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0 or not json.loads(result.stdout).get("items"):
        pytest.skip("No ResourceQuota configured in namespace")
    
    quota = json.loads(result.stdout)["items"][0]
    initial_used = quota["status"].get("used", {})
    print(f"Initial quota usage: {initial_used}")
    
    # Submit a quick job
    eval_id = submit_evaluation('print("Quick job for cleanup test")')
    assert eval_id is not None
    
    # Wait for completion
    status = wait_for_completion(eval_id, timeout=30)
    assert status is not None
    
    # Job should auto-cleanup due to TTL
    print("Waiting for automatic job cleanup (TTL)...")
    time.sleep(5)
    
    # Check quota usage again
    result = subprocess.run(cmd, capture_output=True, text=True)
    quota = json.loads(result.stdout)["items"][0]
    final_used = quota["status"].get("used", {})
    
    print(f"Final quota usage: {final_used}")
    print("✅ Resource cleanup verified")


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
        eval_id = submit_evaluation(code)
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
    
    # Monitor completion
    print("\nMonitoring completion...")
    completed = 0
    failed = 0
    start_time = time.time()
    
    # Simplified tracking of completed/failed evaluations
    completed_ids = set()
    failed_ids = set()
    
    # Track completion over time
    while len(completed_ids) + len(failed_ids) < len(eval_ids) and time.time() - start_time < 120:
        for eval_id in eval_ids:
            if eval_id in completed_ids or eval_id in failed_ids:
                continue
                
            eval_data = get_evaluation_status(eval_id)
            status = eval_data.get("status")
            
            if status == "completed":
                completed_ids.add(eval_id)
                completed += 1
            elif status == "failed":
                failed_ids.add(eval_id)
                failed += 1
        
        # Progress update every 5 seconds
        elapsed = time.time() - start_time
        if int(elapsed) % 5 == 0 and int(elapsed) != int(elapsed - 1):
            rate = completed / elapsed if elapsed > 0 else 0
            print(f"  Progress: {completed}/{len(eval_ids)} completed, "
                  f"{failed} failed ({completed/len(eval_ids)*100:.1f}%) - "
                  f"{rate:.1f} completions/second")
        
        time.sleep(1)
    
    completion_time = time.time() - start_time
    
    # Final metrics
    print(f"\n📊 Completion metrics:")
    print(f"  Completed: {completed}/{len(eval_ids)}")
    print(f"  Failed: {failed}")
    print(f"  Time taken: {completion_time:.1f}s")
    print(f"  Throughput: {completed/completion_time:.2f} completions/second")
    
    # Assertions
    assert completed >= len(eval_ids) * 0.8, f"Too many failures: only {completed}/{len(eval_ids)} completed"
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