#!/usr/bin/env python3
"""
Integration tests for Celery tasks.

This module tests Celery tasks directly without going through the API layer.
It complements test_celery_integration.py which tests the full integration.
"""

import time
import sys
from pathlib import Path
import pytest
from celery import Celery
from celery.result import AsyncResult

# Add celery-worker to path for direct task imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "celery-worker"))


@pytest.mark.integration
@pytest.mark.celery
class TestCeleryTasks:
    """Test Celery tasks directly."""
    
    @pytest.fixture(scope="class")
    def celery_app(self):
        """Create Celery app for testing."""
        from celeryconfig import CELERY_BROKER_URL
        app = Celery("test_tasks", broker=CELERY_BROKER_URL)
        app.conf.update(
            task_serializer="json",
            result_serializer="json",
            accept_content=["json"],
            task_track_started=True,
        )
        return app
    
    def test_health_check_task(self, celery_app):
        """Test the health_check task directly."""
        # Import task after celery app is configured
        from tasks import health_check
        
        # Submit task
        result = health_check.delay()
        assert result.id is not None
        
        # Wait for result with timeout
        response = result.get(timeout=10)
        
        # Verify response
        assert response["status"] == "healthy"
        assert "timestamp" in response
        assert "worker" in response
    
    def test_evaluate_code_task(self, celery_app):
        """Test the evaluate_code task directly."""
        # Import task after celery app is configured
        from tasks import evaluate_code
        
        test_code = """
print("Hello from direct Celery test!")
result = 2 + 2
print(f"2 + 2 = {result}")
"""
        
        # Submit task
        eval_id = f"test-direct-{int(time.time())}"
        result = evaluate_code.delay(eval_id=eval_id, code=test_code, language="python")
        assert result.id is not None
        
        # Monitor task state
        start_time = time.time()
        states_seen = []
        
        while not result.ready() and (time.time() - start_time) < 30:
            current_state = result.state
            if current_state not in states_seen:
                states_seen.append(current_state)
            time.sleep(0.5)
        
        # Get result
        try:
            response = result.get(timeout=5)
            assert response["eval_id"] == eval_id
            assert response["status"] == "completed"
            assert "Hello from direct Celery test!" in response["output"]
            assert "2 + 2 = 4" in response["output"]
            assert response["exit_code"] == 0
        except Exception as e:
            pytest.fail(f"Task execution failed: {e}")
        
        # Verify we saw expected states
        assert "PENDING" in states_seen or "STARTED" in states_seen
    
    def test_multiple_tasks_sequential(self, celery_app):
        """Test submitting multiple tasks sequentially."""
        # Import task after celery app is configured
        from tasks import evaluate_code
        
        tasks = []
        num_tasks = 3
        
        # Submit multiple tasks
        for i in range(num_tasks):
            eval_id = f"test-seq-{i}-{int(time.time())}"
            code = f'print("Sequential task {i}")'
            result = evaluate_code.delay(eval_id=eval_id, code=code, language="python")
            tasks.append((eval_id, result))
            time.sleep(0.1)  # Small delay between submissions
        
        # Wait for all tasks to complete
        completed = 0
        failed = 0
        
        for eval_id, task in tasks:
            try:
                response = task.get(timeout=30)
                assert response["eval_id"] == eval_id
                assert response["status"] == "completed"
                completed += 1
            except Exception as e:
                print(f"Task {eval_id} failed: {e}")
                failed += 1
        
        assert completed == num_tasks
        assert failed == 0
    
    def test_task_state_tracking(self, celery_app):
        """Test that task states are properly tracked."""
        # Import task after celery app is configured
        from tasks import evaluate_code
        
        # Submit a task with a sleep to ensure we can observe STARTED state
        test_code = """
import time
print("Starting task...")
time.sleep(2)  # Give time to observe STARTED state
print("Task completed!")
"""
        
        eval_id = f"test-state-{int(time.time())}"
        result = evaluate_code.delay(eval_id=eval_id, code=test_code, language="python")
        
        # Track state changes
        states = []
        start_time = time.time()
        
        while not result.ready() and (time.time() - start_time) < 10:
            current_state = result.state
            if not states or states[-1] != current_state:
                states.append(current_state)
            time.sleep(0.1)
        
        # Final state
        final_state = result.state
        if final_state not in states:
            states.append(final_state)
        
        # Verify we saw expected state transitions
        assert "SUCCESS" in states
        # STARTED might not always be visible due to timing
        
        # Get the result
        response = result.get(timeout=5)
        assert response["status"] == "completed"