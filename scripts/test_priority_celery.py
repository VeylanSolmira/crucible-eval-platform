#!/usr/bin/env python3
"""Test Celery priority queue by submitting directly to Celery"""

import time
from celery import Celery
from datetime import datetime

# Initialize Celery client
celery_app = Celery("test_client", broker="redis://localhost:6380/0")
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)


def submit_celery_task(code: str, priority: bool = False, name: str = ""):
    """Submit task directly to Celery"""
    eval_id = f"test_{datetime.now().strftime('%H%M%S')}_{name}"
    queue = "high_priority" if priority else "evaluation"

    result = celery_app.send_task(
        "tasks.evaluate_code",
        args=[eval_id, code, "python"],
        queue=queue,
        task_id=f"celery-{eval_id}",
    )

    print(f"{name}: Submitted to {queue} queue - {result.id}")
    return result


def test_celery_priority():
    """Test Celery priority queue processing order"""
    print("=" * 60)
    print("CELERY PRIORITY QUEUE TEST")
    print("=" * 60)
    print("\nSubmitting tasks directly to Celery:")
    print("1. Normal task (sleep 3s)")
    print("2. Normal task (sleep 3s)")
    print("3. HIGH PRIORITY task (quick)")
    print("4. Normal task (sleep 3s)")
    print("\nExpected: HIGH PRIORITY processed first\n")

    # Submit tasks
    tasks = []

    # Normal tasks that take time
    for i in range(2):
        code = f'import time; time.sleep(3); print("Normal task {i + 1} done")'
        result = submit_celery_task(code, priority=False, name=f"normal{i + 1}")
        tasks.append((result, f"Normal {i + 1}", time.time()))
        time.sleep(0.1)

    # High priority task
    code = 'print("HIGH PRIORITY task done!")'
    result = submit_celery_task(code, priority=True, name="priority")
    tasks.append((result, "HIGH PRIORITY", time.time()))
    time.sleep(0.1)

    # Another normal task
    code = 'import time; time.sleep(3); print("Normal task 3 done")'
    result = submit_celery_task(code, priority=False, name="normal3")
    tasks.append((result, "Normal 3", time.time()))

    print("\nMonitoring task completion...\n")

    # Monitor completion
    completed = []
    start_time = time.time()

    while len(completed) < len(tasks) and time.time() - start_time < 30:
        for result, name, submit_time in tasks:
            if not any(r[0].id == result.id for r in completed):
                if result.ready():
                    completion_time = time.time() - start_time
                    completed.append((result, name, completion_time))
                    print(f"✅ {name} completed at {completion_time:.2f}s")
        time.sleep(0.1)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    print("\nCompletion order:")
    for i, (_, name, completion_time) in enumerate(completed, 1):
        print(f"{i}. {name} - {completion_time:.2f}s")

    # Verify priority worked
    if completed and "HIGH PRIORITY" in completed[0][1]:
        print("\n✅ SUCCESS: Celery processed high priority task first!")
    else:
        print("\n❌ FAIL: High priority task was not processed first")

    # Check executor logs
    print("\nTo verify executor-3 usage, check:")
    print("docker logs executor-3 | grep test_")


if __name__ == "__main__":
    test_celery_priority()
