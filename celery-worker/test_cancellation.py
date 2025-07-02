#!/usr/bin/env python3
"""
Test script for Celery task cancellation functionality.
"""

import time
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.app.celery_client import (
    submit_evaluation_to_celery,
    cancel_celery_task,
    get_celery_task_info,
    CELERY_ENABLED,
)


def test_cancellation():
    """Test the cancellation functionality."""

    print("Testing Celery Task Cancellation")
    print("=" * 50)

    # Check if Celery is enabled
    if not CELERY_ENABLED:
        print("❌ Celery is not enabled. Set CELERY_ENABLED=true")
        return

    # Test 1: Cancel a pending task
    print("\n1. Testing cancellation of PENDING task:")
    print("-" * 30)

    # Submit a task
    test_code = """
import time
print("Starting long-running task...")
time.sleep(30)  # Simulate long computation
print("Task completed!")
"""

    eval_id = f"test-cancel-{int(time.time())}"
    task_id = submit_evaluation_to_celery(eval_id, test_code)

    if not task_id:
        print("❌ Failed to submit task")
        return

    print(f"✅ Submitted task with eval_id: {eval_id}")
    print(f"   Task ID: {task_id}")

    # Get initial status
    info = get_celery_task_info(eval_id)
    print(f"   Initial state: {info.get('state', 'UNKNOWN')}")

    # Cancel immediately (while still pending)
    time.sleep(0.5)  # Small delay to ensure it's in queue
    result = cancel_celery_task(eval_id)

    if result.get("cancelled"):
        print(f"✅ Successfully cancelled: {result.get('message')}")
    else:
        print(f"❌ Failed to cancel: {result.get('message')}")

    # Verify final state
    time.sleep(1)
    final_info = get_celery_task_info(eval_id)
    print(f"   Final state: {final_info.get('state', 'UNKNOWN')}")

    # Test 2: Try to cancel an already cancelled task
    print("\n2. Testing cancellation of already CANCELLED task:")
    print("-" * 30)

    result2 = cancel_celery_task(eval_id)
    print(f"   Result: {result2.get('message')}")
    print(f"   Cancelled: {result2.get('cancelled', False)}")

    # Test 3: Test with terminate flag
    print("\n3. Testing cancellation with terminate=True:")
    print("-" * 30)

    eval_id3 = f"test-terminate-{int(time.time())}"
    task_id3 = submit_evaluation_to_celery(eval_id3, test_code)

    if task_id3:
        print(f"✅ Submitted task with eval_id: {eval_id3}")

        # Wait a bit to let it potentially start
        time.sleep(2)

        # Try to terminate
        result3 = cancel_celery_task(eval_id3, terminate=True)
        print(f"   Result: {result3.get('message')}")
        print(f"   Cancelled: {result3.get('cancelled', False)}")

        # Check final state
        time.sleep(1)
        final_info3 = get_celery_task_info(eval_id3)
        print(f"   Final state: {final_info3.get('state', 'UNKNOWN')}")

    print("\n" + "=" * 50)
    print("Test completed!")


if __name__ == "__main__":
    test_cancellation()
