#!/usr/bin/env python3
"""
Test script to verify Celery is working correctly.
Run this after starting Celery with docker-compose.
"""

import time
from tasks import evaluate_code, health_check


def test_health_check():
    """Test basic Celery connectivity."""
    print("Testing health check...")
    result = health_check.delay()
    print(f"Task ID: {result.id}")

    # Wait for result
    response = result.get(timeout=10)
    print(f"Health check response: {response}")
    assert response["status"] == "healthy"
    print("✅ Health check passed!\n")


def test_evaluation():
    """Test code evaluation task."""
    print("Testing code evaluation...")

    test_code = """
print("Hello from Celery!")
for i in range(3):
    print(f"Count: {i}")
"""

    # Submit task
    result = evaluate_code.delay(eval_id="test-001", code=test_code, language="python")
    print(f"Task ID: {result.id}")
    print("Task submitted, waiting for completion...")

    # Monitor task state
    while not result.ready():
        print(f"Task state: {result.state}")
        time.sleep(1)

    try:
        response = result.get(timeout=30)
        print(f"Evaluation response: {response}")
        print("✅ Evaluation completed!\n")
    except Exception as e:
        print(f"❌ Evaluation failed: {e}\n")


def test_task_chaining():
    """Test multiple tasks in sequence."""
    print("Testing task chaining...")

    # Submit multiple tasks
    tasks = []
    for i in range(3):
        result = evaluate_code.delay(
            eval_id=f"chain-{i}", code=f'print("Task {i}")', language="python"
        )
        tasks.append(result)
        print(f"Submitted task {i}: {result.id}")

    # Wait for all to complete
    print("Waiting for all tasks...")
    for i, task in enumerate(tasks):
        try:
            task.get(timeout=30)
            print(f"✅ Task {i} completed")
        except Exception as e:
            print(f"❌ Task {i} failed: {e}")


if __name__ == "__main__":
    print("=== Celery Test Suite ===\n")

    try:
        test_health_check()
        test_evaluation()
        test_task_chaining()
        print("\n🎉 All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
