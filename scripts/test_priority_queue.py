#!/usr/bin/env python3
"""Test priority queue functionality"""
import requests
import time

API_URL = "http://localhost:8000"

def submit_evaluation(code: str, priority: bool = False, test_name: str = "") -> str:
    """Submit an evaluation with optional priority"""
    response = requests.post(
        f"{API_URL}/api/eval",
        json={
            "code": code,
            "language": "python",
            "priority": priority
        }
    )
    if response.status_code == 200:
        eval_id = response.json()["eval_id"]
        print(f"{test_name}: Submitted {'HIGH PRIORITY' if priority else 'normal'} evaluation: {eval_id}")
        return eval_id
    else:
        raise Exception(f"Failed to submit: {response.text}")

def wait_for_completion(eval_id: str, timeout: int = 30) -> tuple:
    """Wait for evaluation to complete and return (status, duration)"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = requests.get(f"{API_URL}/api/evaluations")
        if response.status_code == 200:
            evaluations = response.json().get("evaluations", [])
            for eval_data in evaluations:
                if eval_data.get("eval_id") == eval_id:
                    status = eval_data.get("status", "unknown")
                    if status in ["completed", "failed"]:
                        duration = time.time() - start_time
                        return status, duration
        time.sleep(0.2)
    
    return "timeout", timeout

def test_priority_queue():
    """Test that high priority tasks are processed before normal tasks"""
    print("=" * 60)
    print("PRIORITY QUEUE TEST")
    print("=" * 60)
    print("\nSubmitting tasks in this order:")
    print("1. Normal task (sleep 2s)")
    print("2. Normal task (sleep 2s)")
    print("3. HIGH PRIORITY task (quick)")
    print("4. Normal task (sleep 2s)")
    print("\nExpected: HIGH PRIORITY completes before normal tasks\n")
    
    # Submit evaluations
    eval_ids = []
    
    # Submit 2 normal tasks that will take time
    for i in range(2):
        code = f'import time; time.sleep(2); print("Normal task {i+1} done")'
        eval_id = submit_evaluation(code, priority=False, test_name=f"Task {i+1}")
        eval_ids.append((eval_id, False, f"Normal {i+1}"))
        time.sleep(0.1)  # Small delay between submissions
    
    # Submit high priority task
    code = 'print("HIGH PRIORITY task done!")'
    eval_id = submit_evaluation(code, priority=True, test_name="Task 3")
    eval_ids.append((eval_id, True, "HIGH PRIORITY"))
    time.sleep(0.1)
    
    # Submit another normal task
    code = 'import time; time.sleep(2); print("Normal task 3 done")'
    eval_id = submit_evaluation(code, priority=False, test_name="Task 4")
    eval_ids.append((eval_id, False, "Normal 3"))
    
    print("\nWaiting for completions...\n")
    
    # Track completion order
    completion_order = []
    completed = set()
    start_time = time.time()
    
    while len(completed) < len(eval_ids) and time.time() - start_time < 30:
        for eval_id, is_priority, name in eval_ids:
            if eval_id not in completed:
                status, duration = wait_for_completion(eval_id, timeout=0.5)
                if status == "completed":
                    completed.add(eval_id)
                    completion_time = time.time() - start_time
                    completion_order.append((name, completion_time))
                    print(f"✅ {name} completed at {completion_time:.2f}s")
        time.sleep(0.1)
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    print("\nCompletion order:")
    for i, (name, completion_time) in enumerate(completion_order, 1):
        print(f"{i}. {name} - {completion_time:.2f}s")
    
    # Check if high priority completed first
    if completion_order and "HIGH PRIORITY" in completion_order[0][0]:
        print("\n✅ SUCCESS: High priority task completed first!")
    else:
        print("\n❌ FAIL: High priority task did not complete first")
    
    # Show which executors were used
    print("\nChecking executor usage...")
    print("(Would need to check logs to see which executor processed each task)")

def test_queue_status():
    """Check current queue status"""
    print("\n" + "=" * 60)
    print("QUEUE STATUS")
    print("=" * 60)
    
    try:
        response = requests.get(f"{API_URL}/api/queue-status")
        if response.status_code == 200:
            status = response.json()
            print("\nQueue Status:")
            print(f"  Queued: {status.get('queued', 'N/A')}")
            print(f"  Running: {status.get('running', 'N/A')}")
            print(f"  Workers: {status.get('workers', 'N/A')}")
    except Exception as e:
        print(f"Failed to get queue status: {e}")

if __name__ == "__main__":
    # Check initial status
    test_queue_status()
    
    # Run priority test
    test_priority_queue()
    
    # Check final status
    test_queue_status()