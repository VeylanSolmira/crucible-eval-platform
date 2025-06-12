"""
Task queue for concurrent evaluation processing.
Can evolve into a distributed job queue with Redis/RabbitMQ/SQS.
"""

import queue
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Dict, Any, Callable

from .base import TestableComponent


class TaskQueue(TestableComponent):
    """
    Task queue for concurrent evaluations.
    
    Future evolution:
    - Redis-backed distributed queue
    - Priority queuing
    - Dead letter queue for failed tasks
    - Rate limiting
    - Task persistence
    - Distributed locking
    """
    
    def __init__(self, max_workers: int = 3):
        self.queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.max_workers = max_workers
        self.running = True
        self.active_tasks = {}
        self.completed_count = 0
        self.failed_count = 0
        self.lock = threading.Lock()
        
        # Start worker threads
        for i in range(max_workers):
            self.executor.submit(self._worker, f"worker-{i}")
    
    def submit(self, eval_id: str, func: Callable, *args, **kwargs) -> None:
        """Submit a task to the queue"""
        task = {
            'eval_id': eval_id,
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'submitted_at': datetime.now(timezone.utc)
        }
        self.queue.put(task)
        with self.lock:
            self.active_tasks[eval_id] = 'queued'
    
    def _worker(self, worker_name: str) -> None:
        """Worker thread that processes tasks"""
        while self.running:
            try:
                task = self.queue.get(timeout=1)
                eval_id = task['eval_id']
                
                # Update status
                with self.lock:
                    self.active_tasks[eval_id] = 'running'
                
                # Execute the task
                try:
                    task['func'](*task['args'], **task['kwargs'])
                    with self.lock:
                        self.active_tasks[eval_id] = 'completed'
                        self.completed_count += 1
                except Exception as e:
                    with self.lock:
                        self.active_tasks[eval_id] = f'failed: {str(e)}'
                        self.failed_count += 1
                finally:
                    self.queue.task_done()
                    
            except queue.Empty:
                continue
            except Exception as e:
                # Log unexpected errors but keep worker alive
                print(f"Worker {worker_name} error: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get queue status"""
        with self.lock:
            return {
                'queued': self.queue.qsize(),
                'active_tasks': dict(self.active_tasks),
                'workers': self.max_workers,
                'completed': self.completed_count,
                'failed': self.failed_count,
                'running': self.running
            }
    
    def wait_for_task(self, eval_id: str, timeout: float = 30) -> str:
        """Wait for a specific task to complete"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self.lock:
                status = self.active_tasks.get(eval_id, 'not_found')
                if status in ['completed', 'not_found'] or status.startswith('failed:'):
                    return status
            time.sleep(0.1)
        return 'timeout'
    
    def shutdown(self, wait: bool = True) -> None:
        """Gracefully shutdown the queue"""
        self.running = False
        if wait:
            # Wait for queue to empty
            self.queue.join()
        self.executor.shutdown(wait=wait)
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for the queue"""
        with self.lock:
            healthy = self.running and self.executor._shutdown == False
            return {
                'healthy': healthy,
                'component': 'TaskQueue',
                'queue_size': self.queue.qsize(),
                'active_workers': sum(1 for t in self.executor._threads if t),
                'total_processed': self.completed_count + self.failed_count
            }
    
    def self_test(self) -> Dict[str, Any]:
        """Test queue functionality"""
        tests_passed = []
        tests_failed = []
        
        # Test 1: Task submission and execution
        try:
            result = {'executed': False}
            
            def test_task():
                result['executed'] = True
            
            self.submit('test-1', test_task)
            status = self.wait_for_task('test-1', timeout=2)
            
            if result['executed'] and status == 'completed':
                tests_passed.append("Basic task execution")
            else:
                tests_failed.append(f"Basic task execution: executed={result['executed']}, status={status}")
        except Exception as e:
            tests_failed.append(f"Basic task execution: {str(e)}")
        
        # Test 2: Concurrent execution
        try:
            execution_times = []
            
            def timed_task(task_id: int):
                start = time.time()
                time.sleep(0.3)  # Simulate work
                execution_times.append((task_id, time.time() - start))
            
            # Submit tasks that would take 1.5s if sequential
            start_time = time.time()
            for i in range(5):
                self.submit(f'concurrent-{i}', timed_task, i)
            
            # Wait for all tasks
            self.queue.join()
            elapsed = time.time() - start_time
            
            # With 3 workers, should complete in ~0.5s, not 1.5s
            # Allow some overhead for thread management
            if elapsed < 1.0 and len(execution_times) == 5:
                tests_passed.append("Concurrent execution")
            else:
                tests_failed.append(f"Concurrent execution: elapsed={elapsed:.2f}s, tasks={len(execution_times)}")
        except Exception as e:
            tests_failed.append(f"Concurrent execution: {str(e)}")
        
        # Test 3: Error handling
        try:
            def failing_task():
                raise ValueError("Test exception")
            
            self.submit('fail-test', failing_task)
            status = self.wait_for_task('fail-test', timeout=2)
            
            if status.startswith('failed:') and 'Test exception' in status:
                tests_passed.append("Error handling")
            else:
                tests_failed.append(f"Error handling: status={status}")
        except Exception as e:
            tests_failed.append(f"Error handling: {str(e)}")
        
        # Test 4: Queue status
        try:
            status = self.get_status()
            if isinstance(status, dict) and 'queued' in status and 'workers' in status:
                tests_passed.append("Status reporting")
            else:
                tests_failed.append("Status reporting: invalid status format")
        except Exception as e:
            tests_failed.append(f"Status reporting: {str(e)}")
        
        return {
            'passed': len(tests_failed) == 0,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'message': f"Passed {len(tests_passed)}/{len(tests_passed) + len(tests_failed)} tests"
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Return unittest suite for queue"""
        queue_instance = self
        
        class QueueTests(unittest.TestCase):
            def setUp(self):
                # Use existing queue instance for tests
                self.queue = queue_instance
            
            def test_submission_and_execution(self):
                """Test basic task submission and execution"""
                result = {'value': None}
                
                def set_value(val):
                    result['value'] = val
                
                self.queue.submit('test-sub', set_value, 42)
                status = self.queue.wait_for_task('test-sub')
                
                self.assertEqual(status, 'completed')
                self.assertEqual(result['value'], 42)
            
            def test_multiple_workers(self):
                """Test that multiple workers process tasks concurrently"""
                results = []
                lock = threading.Lock()
                
                def add_worker_id():
                    # Get current thread name
                    worker_id = threading.current_thread().name
                    with lock:
                        results.append(worker_id)
                    time.sleep(0.1)
                
                # Submit more tasks than workers
                for i in range(10):
                    self.queue.submit(f'worker-test-{i}', add_worker_id)
                
                self.queue.queue.join()
                
                # Should see multiple different worker IDs
                unique_workers = len(set(results))
                self.assertGreater(unique_workers, 1, "Should use multiple workers")
                self.assertEqual(len(results), 10, "All tasks should complete")
            
            def test_error_recovery(self):
                """Test that queue continues after task failures"""
                def failing_task():
                    raise RuntimeError("Intentional failure")
                
                def succeeding_task():
                    return "success"
                
                # Submit failing task
                self.queue.submit('fail-1', failing_task)
                fail_status = self.queue.wait_for_task('fail-1')
                self.assertTrue(fail_status.startswith('failed:'))
                
                # Queue should still work
                result = {'success': False}
                def mark_success():
                    result['success'] = True
                
                self.queue.submit('success-1', mark_success)
                success_status = self.queue.wait_for_task('success-1')
                
                self.assertEqual(success_status, 'completed')
                self.assertTrue(result['success'])
        
        return unittest.TestLoader().loadTestsFromTestCase(QueueTests)