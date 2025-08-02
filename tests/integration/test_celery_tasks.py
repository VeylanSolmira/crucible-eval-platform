#!/usr/bin/env python3
"""
Integration tests for Celery tasks.

This module tests Celery tasks directly without going through the API layer.
It complements test_celery_integration.py which tests the full integration.
"""

import time
import pytest
import httpx
from celery import Celery
from celery.result import AsyncResult
from k8s_test_config import STORAGE_SERVICE_URL
from storage_service.app import EvaluationCreate


@pytest.mark.whitebox
@pytest.mark.integration
@pytest.mark.celery
class TestCeleryTasks:
    """Test Celery tasks directly."""
    
    @pytest.fixture(scope="class")
    def celery_app(self):
        """Create Celery app for testing."""
        from k8s_test_config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND
        
        app = Celery("test_tasks")
        
        # Configure directly without importing celeryconfig
        app.conf.update(
            broker_url=CELERY_BROKER_URL,
            result_backend=CELERY_RESULT_BACKEND,
            task_serializer="json",
            result_serializer="json",
            accept_content=["json"],
            task_track_started=True,
            task_always_eager=False,
            task_eager_propagates=True,
            # Match worker's queue configuration
            task_default_queue='evaluation',
            task_default_exchange='crucible',
            task_default_routing_key='evaluation'
        )
        
        return app
    
    def test_health_check_task(self, celery_app):
        """Test the health_check task directly."""
        # Use task signature to send task by name
        result = celery_app.send_task('celery_worker.tasks.health_check')
        assert result.id is not None
        
        # Wait for result with timeout
        response = result.get(timeout=10)
        
        # Verify response
        assert response["status"] == "healthy"
        assert "worker" in response
    
    def test_evaluate_code_task(self, celery_app):
        """Test the evaluate_code task directly."""
        test_code = """
print("Hello from direct Celery test!")
result = 2 + 2
print(f"2 + 2 = {result}")
"""
        
        # Create evaluation in storage first
        eval_id = f"test-direct-{int(time.time())}"
        evaluation = EvaluationCreate(
            id=eval_id,
            code=test_code,
            language="python"
        )
        with httpx.Client() as client:
            response = client.post(
                f"{STORAGE_SERVICE_URL}/evaluations",
                json=evaluation.model_dump()
            )
            assert response.status_code == 200  # Storage service returns 200, not 201
        
        # Submit task using send_task with correct argument order
        # evaluate_code(self, eval_id, code, language="python", timeout=300, priority=0, ...)
        result = celery_app.send_task(
            'celery_worker.tasks.evaluate_code',
            args=[eval_id, test_code, "python", 300, -1]  # language, timeout, priority
        )
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
            assert response["status"] == "created"  # Job creation status
            assert "job_name" in response  # Verify K8s job was created
            # Output not available yet - job runs async
        except Exception as e:
            pytest.fail(f"Task execution failed: {e}")
        finally:
            # Clean up evaluation
            with httpx.Client() as client:
                client.delete(f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}")
        
        # Verify we saw expected states
        assert "PENDING" in states_seen or "STARTED" in states_seen
    
    def test_multiple_tasks_sequential(self, celery_app):
        """Test submitting multiple tasks sequentially."""
        tasks = []
        num_tasks = 3
        created_evals = []
        
        try:
            # Create evaluations and submit tasks
            for i in range(num_tasks):
                eval_id = f"test-seq-{i}-{int(time.time())}"
                code = f'print("Sequential task {i}")'
                
                # Create evaluation in storage
                evaluation = EvaluationCreate(
                    id=eval_id,
                    code=code,
                    language="python"
                )
                with httpx.Client() as client:
                    response = client.post(
                        f"{STORAGE_SERVICE_URL}/evaluations",
                        json=evaluation.model_dump()
                    )
                    assert response.status_code == 200  # Storage service returns 200, not 201
                    created_evals.append(eval_id)
                
                # Submit task
                result = celery_app.send_task(
                    'celery_worker.tasks.evaluate_code',
                    args=[eval_id, code, "python", 300, -1]  # language, timeout, priority
                )
                tasks.append((eval_id, result))
                time.sleep(0.1)  # Small delay between submissions
        
            # Wait for all tasks to complete
            completed = 0
            failed = 0
            
            for eval_id, task in tasks:
                try:
                    response = task.get(timeout=30)
                    assert response["eval_id"] == eval_id
                    assert response["status"] == "created"
                    assert "job_name" in response
                    completed += 1
                except Exception as e:
                    print(f"Task {eval_id} failed: {e}")
                    failed += 1
            
            assert completed == num_tasks
            assert failed == 0
        finally:
            # Clean up evaluations
            with httpx.Client() as client:
                for eval_id in created_evals:
                    client.delete(f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}")
    
    def test_task_state_tracking(self, celery_app):
        """Test that task states are properly tracked.
        
        Note: Tasks may enter RETRY state due to capacity constraints or 
        transient HTTP errors, especially in resource-constrained test environments.
        """
        # Submit a task with a sleep to ensure we can observe STARTED state
        test_code = """
import time
print("Starting task...")
time.sleep(2)  # Give time to observe STARTED state
print("Task completed!")
"""
        
        eval_id = f"test-state-{int(time.time())}"
        
        # Create evaluation in storage
        evaluation = EvaluationCreate(
            id=eval_id,
            code=test_code,
            language="python"
        )
        with httpx.Client() as client:
            response = client.post(
                f"{STORAGE_SERVICE_URL}/evaluations",
                json=evaluation.model_dump()
            )
            assert response.status_code == 200  # Storage service returns 200, not 201
        
        try:
            result = celery_app.send_task(
                'celery_worker.tasks.evaluate_code',
                args=[eval_id, test_code, "python", 300, -1]  # language, timeout, priority
            )
        
            # Track state changes
            states = []
            start_time = time.time()
            
            while not result.ready() and (time.time() - start_time) < 30:  # Increased timeout
                current_state = result.state
                if not states or states[-1] != current_state:
                    states.append(current_state)
                time.sleep(0.1)
            
            # Final state
            final_state = result.state
            if final_state not in states:
                states.append(final_state)
            
            # Verify we saw expected state transitions or retry behavior
            # Task may retry due to capacity constraints or transient errors
            assert "SUCCESS" in states or "RETRY" in states
            # STARTED might not always be visible due to timing
            
            # Get the result
            try:
                response = result.get(timeout=20)
                assert response["status"] == "created"
                assert "job_name" in response
            except Exception as e:
                pytest.fail(f"Task failed: {e}")
        finally:
            # Clean up evaluation
            with httpx.Client() as client:
                client.delete(f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}")