#!/usr/bin/env python3
"""
DEPRECATED: Old Docker-based evaluation workflow tests

This test suite was written for the Docker executor pool pattern which no longer exists.
It has been replaced by test_evaluation_workflows_k8s.py which tests Kubernetes-native behavior.

These tests are kept for historical reference showing the old architecture:
- Fixed pool of executor containers
- Executors were allocated/released for each evaluation
- Tasks would queue when all executors were busy

The new Kubernetes tests validate:
- Jobs are created on-demand (no fixed pool)
- No allocation/release - Jobs are created and destroyed
- Queueing happens at the Kubernetes scheduler level
- Resource limits are enforced by ResourceQuotas

See: test_evaluation_workflows_k8s.py for the current implementation
"""

import os
import time
import json
import pytest
import redis
import httpx
from celery import Celery
import urllib3

# INTENTIONALLY SKIPPED: These tests need to be rewritten for Kubernetes architecture
# They assume the old Docker executor pool pattern which no longer exists
# See: docs/planning/sprints/week-6-crucible-platform.md section 15
pytestmark = pytest.mark.skip(reason="Needs rewrite for Kubernetes - uses executor pool pattern")

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6380/0")  # Celery Redis on 6380
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
STORAGE_SERVICE_URL = os.environ.get("STORAGE_SERVICE_URL", "http://localhost:8082")
API_URL = os.environ.get("API_URL", "https://localhost")  # Use HTTPS with nginx
VERIFY_SSL = False  # Disable SSL verification for self-signed cert

# Pytest fixtures
@pytest.fixture(scope="module")
def redis_client():
    """Redis client fixture"""
    return redis.from_url(REDIS_URL)

@pytest.fixture(scope="module")
def celery_app():
    """Celery app fixture"""
    app = Celery("test_client", broker=CELERY_BROKER_URL)
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
    )
    return app

@pytest.fixture(scope="module", autouse=True)
def check_services_DISABLED():
    """DISABLED: This fixture checks localhost URLs which don't work in Kubernetes.
    
    The module-level skip marker above takes precedence anyway.
    Keeping this here to show what needs updating when we rewrite these tests.
    """
    try:
        httpx.get(f"{API_URL}/health", timeout=2, follow_redirects=True, verify=VERIFY_SSL)
        httpx.get(f"{STORAGE_SERVICE_URL}/health", timeout=2, follow_redirects=True, verify=VERIFY_SSL)
    except Exception as e:
        pytest.skip(f"Services not running: {e}", allow_module_level=True)


# Helper functions
def check_celery_task_chain_info(redis_client, eval_id: str):
    """Check Celery task chain information for an evaluation."""
    print(f"\n🔗 Checking task chain for {eval_id}:")
    
    # Check for assigner task
    assigner_id = redis_client.get(f"assigner:{eval_id}")
    if assigner_id:
        print(f"  Assigner task: {assigner_id.decode()}")
    
    # Check for task mapping
    task_id = redis_client.get(f"task_mapping:{eval_id}")
    if task_id:
        print(f"  Evaluation task: {task_id.decode()}")
    
    # Check Celery result backend for task info
    # This would show parent/child relationships if available


def check_executor_pool(redis_client, detailed=False):
    """Check the current state of the executor pool."""
    print("\n🔍 Checking executor pool status...")
    
    available_count = redis_client.llen("executors:available")
    print(f"Available executors: {available_count}")
    
    # Get detailed available executor list if requested
    if detailed and available_count > 0:
        print("  Available executor details:")
        available_executors = redis_client.lrange("executors:available", 0, -1)
        seen_urls = set()
        for i, executor_data in enumerate(available_executors):
            data = json.loads(executor_data)
            url = data.get("url", "unknown")
            if url in seen_urls:
                print(f"    [{i}] {url} - ⚠️  DUPLICATE!")
            else:
                print(f"    [{i}] {url}")
            seen_urls.add(url)
    
    # Check busy executors
    busy_keys = list(redis_client.scan_iter(match="executor:busy:*"))
    print(f"Busy executors: {len(busy_keys)}")
    
    for key in busy_keys:
        executor_url = key.decode().replace("executor:busy:", "")
        eval_id = redis_client.get(key)
        ttl = redis_client.ttl(key)
        print(f"  - {executor_url}: eval_id={eval_id.decode() if eval_id else 'None'}, ttl={ttl}s")
    
    return available_count, len(busy_keys)


def submit_evaluation_via_api(code: str, test_name: str) -> str:
    """Submit evaluation through the API (uses task chaining)."""
    print(f"\n📤 Submitting {test_name} via API...")
    
    response = httpx.post(
        f"{API_URL}/api/eval",
        json={"code": code, "language": "python"},
        timeout=10.0,
        follow_redirects=True,
        verify=VERIFY_SSL
    )
    
    if response.status_code not in [200, 202]:  # Accept both 200 and 202
        print(f"❌ Failed to submit: {response.status_code} - {response.text}")
        return None
        
    result = response.json()
    eval_id = result.get("eval_id") or result.get("id")  # Handle different response formats
    print(f"✅ Submitted evaluation {eval_id}")
    return eval_id


def monitor_evaluation(eval_id: str, timeout: int = 30) -> dict:
    """Monitor evaluation status until completion."""
    print(f"\n📊 Monitoring evaluation {eval_id}...")
    
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < timeout:
        try:
            response = httpx.get(f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}", follow_redirects=True, verify=VERIFY_SSL)
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "unknown")
                
                if status != last_status:
                    print(f"  Status: {status}")
                    last_status = status
                
                if status in ["completed", "failed"]:
                    return data
                    
        except Exception as e:
            print(f"  Error checking status: {e}")
        
        time.sleep(1)
    
    print(f"⏱️  Timeout after {timeout} seconds")
    return None


# Test functions
@pytest.mark.whitebox
@pytest.mark.api
def test_single_evaluation(redis_client):
    """Test a single evaluation through the full chain."""
    print("\n" + "="*60)
    print("TEST 1: Single Evaluation")
    print("="*60)
    
    initial_available, initial_busy = check_executor_pool(redis_client)
    
    eval_id = submit_evaluation_via_api(
        code='print("Hello from task chaining!")',
        test_name="single evaluation"
    )
    
    assert eval_id is not None, "Failed to submit evaluation"
    
    result = monitor_evaluation(eval_id)
    assert result is not None, "Evaluation timed out"
    assert result["status"] == "completed", f"Evaluation failed: {result.get('error')}"
    
    print(f"\n✅ Evaluation completed!")
    print(f"  Output: {result.get('output', 'N/A')}")
    print(f"  Error: {result.get('error', 'None')}")
    print(f"  Executor: {result.get('executor_id', 'N/A')}")
    
    # Verify executor was released
    final_available, final_busy = check_executor_pool(redis_client)
    assert final_available == initial_available, "Executor not properly released"
    assert final_busy == initial_busy, "Executor still marked as busy"


@pytest.mark.api
def test_concurrent_evaluations(redis_client):
    """Test multiple concurrent evaluations to verify executor allocation."""
    print("\n" + "="*60)
    print("TEST 2: Concurrent Evaluations")
    print("="*60)
    
    initial_available, initial_busy = check_executor_pool(redis_client)
    
    # Submit multiple evaluations
    eval_ids = []
    for i in range(5):
        code = f'import time; time.sleep(2); print("Task {i} completed")'
        eval_id = submit_evaluation_via_api(
            code=code,
            test_name=f"concurrent task {i}"
        )
        if eval_id:
            eval_ids.append(eval_id)
        time.sleep(0.1)  # Small delay between submissions
    
    assert len(eval_ids) >= 3, f"Only {len(eval_ids)} evaluations submitted, expected at least 3"
    print(f"\n📋 Submitted {len(eval_ids)} evaluations")
    
    # Monitor all evaluations
    results = {}
    start_time = time.time()
    timeout = 60
    
    while len(results) < len(eval_ids) and time.time() - start_time < timeout:
        for eval_id in eval_ids:
            if eval_id not in results:
                try:
                    response = httpx.get(f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}", verify=VERIFY_SSL)
                    if response.status_code == 200:
                        data = response.json()
                        status = data.get("status", "unknown")
                        
                        if status in ["completed", "failed"]:
                            results[eval_id] = data
                            print(f"  {eval_id}: {status}")
                            
                except Exception:
                    pass
        
        check_executor_pool(redis_client)
        time.sleep(2)
    
    # Verify results
    completed_count = sum(1 for r in results.values() if r.get('status') == 'completed')
    failed_count = sum(1 for r in results.values() if r.get('status') == 'failed')
    
    print(f"\n📊 Results Summary:")
    print(f"  Total submitted: {len(eval_ids)}")
    print(f"  Completed: {completed_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Time elapsed: {time.time() - start_time:.1f}s")
    
    assert len(results) == len(eval_ids), f"Only {len(results)}/{len(eval_ids)} evaluations finished"
    assert completed_count >= len(eval_ids) - 1, f"Too many failures: {failed_count}/{len(eval_ids)}"
    
    # Verify executors were released
    final_available, final_busy = check_executor_pool(redis_client)
    assert final_available == initial_available, "Some executors not properly released"
    assert final_busy == initial_busy, "Some executors still marked as busy"


@pytest.mark.api
def test_executor_shortage(redis_client):
    """Test behavior when there are more tasks than executors."""
    print("\n" + "="*60)
    print("TEST 3: Executor Shortage (More Tasks than Executors)")
    print("="*60)
    
    initial_available, _ = check_executor_pool(redis_client)
    
    # Submit more tasks than we have executors
    eval_ids = []
    num_tasks = initial_available + 3  # Submit 3 more than available
    
    for i in range(num_tasks):
        code = f'import time; time.sleep(5); print("Long task {i}")'
        eval_id = submit_evaluation_via_api(
            code=code,
            test_name=f"shortage task {i}"
        )
        if eval_id:
            eval_ids.append(eval_id)
    
    print(f"\n📋 Submitted {len(eval_ids)} evaluations (expecting queueing)")
    assert len(eval_ids) == num_tasks, f"Failed to submit all {num_tasks} tasks"
    
    # Monitor queue status for 10 seconds
    max_queued = 0
    for i in range(10):
        print(f"\n⏱️  Time: {i*2}s")
        available, busy = check_executor_pool(redis_client)
        
        # Check task statuses
        statuses = {}
        for eval_id in eval_ids:
            try:
                response = httpx.get(f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}", verify=VERIFY_SSL)
                if response.status_code == 200:
                    status = response.json().get("status", "unknown")
                    statuses[status] = statuses.get(status, 0) + 1
            except Exception:
                pass
        
        print(f"  Task statuses: {statuses}")
        
        # Track maximum number of queued tasks
        queued = statuses.get("queued", 0) + statuses.get("submitted", 0)
        max_queued = max(max_queued, queued)
        
        time.sleep(2)
    
    # Verify queueing occurred
    assert max_queued > 0, "No tasks were queued despite executor shortage"


@pytest.mark.api
def test_task_cancellation(redis_client):
    """Test cancelling a task during execution."""
    print("\n" + "="*60)
    print("TEST 4: Task Cancellation")
    print("="*60)
    
    # Submit a long-running task
    code = 'import time; time.sleep(30); print("Should be cancelled")'
    eval_id = submit_evaluation_via_api(
        code=code,
        test_name="cancellation test"
    )
    
    assert eval_id is not None, "Failed to submit evaluation for cancellation"
    
    time.sleep(1)
    
    # Cancel the task
    print(f"\n🚫 Cancelling evaluation {eval_id}...")
    response = httpx.post(f"{API_URL}/api/eval/{eval_id}/cancel", verify=VERIFY_SSL)
    
    assert response.status_code == 200, f"Failed to cancel: {response.status_code}"
    
    result = response.json()
    print(f"  Cancellation result: {result}")
    
    # Check final status
    time.sleep(2)
    response = httpx.get(f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}", verify=VERIFY_SSL)
    assert response.status_code == 200, "Failed to retrieve cancelled evaluation"
    
    final_status = response.json().get("status")
    print(f"  Final status: {final_status}")
    
    # Cancelled tasks may show as failed or cancelled depending on timing
    assert final_status in ["failed", "cancelled"], f"Unexpected status: {final_status}"


@pytest.mark.slow
@pytest.mark.api
def test_high_load(redis_client):
    """Test system under high load with many tasks."""
    print("\n" + "="*60)
    print("TEST 5: High Load (50 Tasks)")
    print("="*60)
    
    initial_available, initial_busy = check_executor_pool(redis_client)
    
    # Submit 50 tasks
    eval_ids = []
    batch_size = 50
    print(f"\n📋 Submitting {batch_size} evaluations...")
    
    start_time = time.time()
    for i in range(batch_size):
        code = f'import time; time.sleep(0.5); print("Task {i} completed")'
        eval_id = submit_evaluation_via_api(
            code=code,
            test_name=f"load task {i}"
        )
        if eval_id:
            eval_ids.append(eval_id)
            # Small progress indicator every 10 tasks
            if (i + 1) % 10 == 0:
                print(f"  Submitted {i + 1}/{batch_size} tasks...")
        # Add small delay to avoid rate limiting
        time.sleep(0.1)
    
    submission_time = time.time() - start_time
    assert len(eval_ids) >= batch_size * 0.9, f"Failed to submit enough tasks: {len(eval_ids)}/{batch_size}"
    
    print(f"\n📊 Submitted {len(eval_ids)} evaluations in {submission_time:.1f}s")
    print(f"  Average submission rate: {len(eval_ids)/submission_time:.1f} tasks/second")
    
    # Monitor completion
    print("\n⏳ Monitoring task completion...")
    results = {}
    completed_timeline = []
    monitor_start = time.time()
    last_print_time = monitor_start
    
    while len(results) < len(eval_ids):
        current_time = time.time()
        elapsed = current_time - monitor_start
        
        # Check status of all tasks
        for eval_id in eval_ids:
            if eval_id not in results:
                try:
                    response = httpx.get(
                        f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}", 
                        follow_redirects=True, 
                        verify=VERIFY_SSL
                    )
                    if response.status_code == 200:
                        data = response.json()
                        status = data.get("status", "unknown")
                        
                        if status in ["completed", "failed"]:
                            results[eval_id] = data
                            completed_timeline.append((elapsed, status))
                except Exception:
                    pass
        
        # Print progress every 5 seconds
        if current_time - last_print_time >= 5:
            # Get current pool status
            available_before = redis_client.llen("executors:available")
            check_executor_pool(redis_client)
            
            # If we see more than expected executors, do detailed check
            if available_before > 3:
                print(f"  ⚠️  ANOMALY DETECTED: {available_before} executors (expected max 3)")
                check_executor_pool(redis_client, detailed=True)
            
            completed_count = len(results)
            remaining = len(eval_ids) - completed_count
            rate = completed_count / elapsed if elapsed > 0 else 0
            
            print(f"  Progress: {completed_count}/{len(eval_ids)} completed "
                  f"({completed_count/len(eval_ids)*100:.1f}%) - "
                  f"{rate:.1f} tasks/second - "
                  f"{remaining} remaining")
            last_print_time = current_time
        
        # Break if taking too long
        if elapsed > 300:  # 5 minutes timeout
            print(f"⏱️  Timeout after {elapsed:.1f}s")
            break
        
        time.sleep(0.5)
    
    # Final statistics
    total_time = time.time() - monitor_start
    completed_count = sum(1 for r in results.values() if r.get('status') == 'completed')
    failed_count = sum(1 for r in results.values() if r.get('status') == 'failed')
    
    print(f"\n📊 High Load Test Results:")
    print(f"  Total tasks: {batch_size}")
    print(f"  Submitted: {len(eval_ids)}")
    print(f"  Completed: {completed_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Missing: {batch_size - len(results)}")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Throughput: {completed_count/total_time:.2f} tasks/second")
    
    # Assertions
    assert completed_count >= len(eval_ids) * 0.8, f"Too many failures: only {completed_count}/{len(eval_ids)} completed"
    assert total_time < 300, f"Test took too long: {total_time}s"
    
    # Analyze completion timeline
    if completed_timeline:
        completion_times = [t for t, _ in completed_timeline]
        print(f"\n  Completion timeline:")
        print(f"    First task completed: {min(completion_times):.1f}s")
        print(f"    Last task completed: {max(completion_times):.1f}s")
        print(f"    Average completion time: {sum(completion_times)/len(completion_times):.1f}s")
    
    # Verify executors were released
    final_available, final_busy = check_executor_pool(redis_client)
    assert final_available == initial_available, "Some executors not properly released after high load"
    assert final_busy == initial_busy, "Some executors still marked as busy after high load"


if __name__ == "__main__":
    # Allow running with pytest directly
    import subprocess
    import sys
    sys.exit(subprocess.call(["pytest", __file__, "-v"]))