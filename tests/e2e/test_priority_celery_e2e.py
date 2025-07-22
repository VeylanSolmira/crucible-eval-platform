"""
End-to-end tests for Celery priority queue functionality.

These tests verify the complete task execution flow with priority handling:
1. Tasks can be submitted directly to Celery with different priorities
2. High priority tasks are processed before normal priority tasks
3. The priority queue system is working as expected through full execution

NOTE: These tests are currently SKIPPED because Redis does not support true priority
queues. With Redis, Celery checks queues in round-robin fashion, providing only
partial prioritization (~50% preference for high-priority tasks).

For true priority queue support, we would need to migrate to RabbitMQ.
See: docs/architecture/celery-redis-vs-rabbitmq.md

When/if we migrate to RabbitMQ, these tests should be re-enabled and will pass.
"""

import pytest
import time
from celery import Celery
from datetime import datetime
from typing import List, Tuple, Any
from k8s_test_config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND


@pytest.fixture
def celery_client():
    """Create a Celery client for testing."""
    celery_app = Celery("test_client", broker=CELERY_BROKER_URL)
    celery_app.conf.update(
        result_backend=CELERY_RESULT_BACKEND,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
    )
    return celery_app


def submit_celery_task(celery_app: Celery, code: str, priority: bool = False, name: str = "") -> Any:
    """Submit task directly to Celery."""
    eval_id = f"test_{datetime.now().strftime('%H%M%S')}_{name}"
    queue = "high_priority" if priority else "evaluation"

    result = celery_app.send_task(
        "celery_worker.tasks.evaluate_code",
        args=[eval_id, code, "python"],
        queue=queue,
        task_id=f"celery-{eval_id}",
    )

    return result, eval_id, queue


@pytest.mark.e2e
@pytest.mark.whitebox
@pytest.mark.celery
@pytest.mark.skip(reason="Redis doesn't support true priority queues. See docs/architecture/celery-redis-vs-rabbitmq.md")
def test_celery_priority_queue_order(celery_client):
    """Test that Celery processes high priority tasks first."""
    
    # Submit tasks
    tasks = []
    
    # Normal tasks that take time
    for i in range(2):
        code = f'import time; time.sleep(2); print("Normal task {i + 1} done")'
        result, eval_id, queue = submit_celery_task(
            celery_client, code, priority=False, name=f"normal{i + 1}"
        )
        tasks.append((result, f"Normal {i + 1}", time.time(), queue))
        time.sleep(0.1)
    
    # High priority task (quick)
    code = 'print("HIGH PRIORITY task done!")'
    result, eval_id, queue = submit_celery_task(
        celery_client, code, priority=True, name="priority"
    )
    tasks.append((result, "HIGH PRIORITY", time.time(), queue))
    time.sleep(0.1)
    
    # Another normal task
    code = 'import time; time.sleep(2); print("Normal task 3 done")'
    result, eval_id, queue = submit_celery_task(
        celery_client, code, priority=False, name="normal3"
    )
    tasks.append((result, "Normal 3", time.time(), queue))
    
    # Monitor completion
    completed = []
    start_time = time.time()
    timeout = 30
    
    while len(completed) < len(tasks) and time.time() - start_time < timeout:
        for result, name, submit_time, queue in tasks:
            if not any(r[0].id == result.id for r in completed):
                if result.ready():
                    completion_time = time.time() - start_time
                    completed.append((result, name, completion_time))
        time.sleep(0.1)
    
    # Verify all tasks completed
    assert len(completed) == len(tasks), f"Only {len(completed)} of {len(tasks)} tasks completed"
    
    # Verify priority task completed first
    assert completed[0][1] == "HIGH PRIORITY", (
        f"Expected HIGH PRIORITY task to complete first, but {completed[0][1]} completed first"
    )


@pytest.mark.e2e
@pytest.mark.celery
@pytest.mark.skip(reason="Redis doesn't support true priority queues. See docs/architecture/celery-redis-vs-rabbitmq.md")
def test_celery_multiple_priorities(celery_client):
    """Test multiple priority levels with Celery."""
    
    # Submit tasks with different priorities
    tasks = []
    
    # Low priority batch task
    code = 'import time; time.sleep(1); print("Batch task done")'
    result = celery_client.send_task(
        "celery_worker.tasks.batch_evaluation",
        args=[f"test_batch_{datetime.now().strftime('%H%M%S')}", code, "python"],
        queue="batch",
        task_id=f"celery-batch-{datetime.now().strftime('%H%M%S')}",
    )
    tasks.append((result, "Batch", "batch"))
    
    # Normal priority task
    code = 'print("Normal priority task done")'
    result, eval_id, queue = submit_celery_task(
        celery_client, code, priority=False, name="normal"
    )
    tasks.append((result, "Normal", queue))
    
    # High priority task
    code = 'print("High priority task done")'
    result, eval_id, queue = submit_celery_task(
        celery_client, code, priority=True, name="high"
    )
    tasks.append((result, "High", queue))
    
    # Wait for all to complete
    start_time = time.time()
    timeout = 20
    
    while any(not task[0].ready() for task in tasks) and time.time() - start_time < timeout:
        time.sleep(0.1)
    
    # Verify all completed
    for result, name, queue in tasks:
        assert result.ready(), f"{name} task in {queue} queue did not complete"


@pytest.mark.e2e
@pytest.mark.celery
@pytest.mark.slow
@pytest.mark.skip(reason="Redis doesn't support true priority queues. See docs/architecture/celery-redis-vs-rabbitmq.md")
def test_celery_priority_under_load(celery_client):
    """Test priority queue behavior under load."""
    
    # Submit many normal tasks
    normal_tasks = []
    for i in range(5):
        code = f'import time; time.sleep(1); print("Normal task {i} done")'
        result, eval_id, queue = submit_celery_task(
            celery_client, code, priority=False, name=f"load_normal{i}"
        )
        normal_tasks.append((result, f"Normal {i}"))
    
    # Wait a bit to ensure normal tasks are queued
    time.sleep(0.5)
    
    # Submit high priority task
    code = 'print("URGENT: High priority task done!")'
    high_result, eval_id, queue = submit_celery_task(
        celery_client, code, priority=True, name="urgent"
    )
    
    # Monitor which completes first
    start_time = time.time()
    high_completed = False
    normal_completed = 0
    
    while time.time() - start_time < 30:
        if not high_completed and high_result.ready():
            high_completed = True
            high_completion_time = time.time() - start_time
            
        for result, name in normal_tasks:
            if result.ready():
                normal_completed += 1
                
        if high_completed:
            break
            
        time.sleep(0.1)
    
    assert high_completed, "High priority task did not complete"
    
    # High priority should complete even if submitted after normal tasks
    assert high_completion_time < 5, (
        f"High priority task took too long ({high_completion_time:.2f}s) to complete"
    )


if __name__ == "__main__":
    # Allow running directly for debugging
    pytest.main([__file__, "-v", "-s"])