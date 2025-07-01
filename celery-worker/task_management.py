"""
Task management utilities for Celery.

This module provides utilities for managing Celery tasks including
cancellation, status tracking, and task introspection.
"""
import logging
from typing import Dict, Any, Optional, List
from celery import Celery
from celery.result import AsyncResult
from celery.task.control import revoke

logger = logging.getLogger(__name__)

class TaskManager:
    """Manages Celery task lifecycle and operations."""
    
    def __init__(self, celery_app: Celery):
        self.app = celery_app
    
    def cancel_task(self, task_id: str, terminate: bool = False) -> Dict[str, Any]:
        """
        Cancel a Celery task.
        
        Args:
            task_id: The Celery task ID to cancel
            terminate: If True, terminate the task if it's already running.
                      If False, only cancel if still in queue.
        
        Returns:
            Dictionary with cancellation status and details
        """
        try:
            # Get task result object
            result = AsyncResult(task_id, app=self.app)
            
            # Check current task state
            task_state = result.state
            task_info = result.info
            
            response = {
                "task_id": task_id,
                "previous_state": task_state,
                "task_info": task_info,
                "cancelled": False,
                "message": ""
            }
            
            # Handle different task states
            if task_state == 'PENDING':
                # Task is still in queue, can be safely cancelled
                revoke(task_id, app=self.app)
                response["cancelled"] = True
                response["message"] = "Task cancelled successfully (was pending)"
                logger.info(f"Cancelled pending task {task_id}")
                
            elif task_state in ['STARTED', 'RETRY']:
                # Task is running or retrying
                if terminate:
                    # Force termination of running task
                    revoke(task_id, app=self.app, terminate=True)
                    response["cancelled"] = True
                    response["message"] = "Task terminated (was running)"
                    logger.warning(f"Terminated running task {task_id}")
                else:
                    response["message"] = "Task is already running. Use terminate=true to force stop."
                    
            elif task_state in ['SUCCESS', 'FAILURE']:
                # Task already completed
                response["message"] = f"Task already completed with state: {task_state}"
                
            elif task_state == 'REVOKED':
                # Task was already cancelled
                response["message"] = "Task was already cancelled"
                
            else:
                # Unknown state
                response["message"] = f"Unknown task state: {task_state}"
            
            return response
            
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return {
                "task_id": task_id,
                "cancelled": False,
                "error": str(e),
                "message": "Failed to cancel task"
            }
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get detailed status of a Celery task.
        
        Args:
            task_id: The Celery task ID
            
        Returns:
            Dictionary with task status information
        """
        try:
            result = AsyncResult(task_id, app=self.app)
            
            status = {
                "task_id": task_id,
                "state": result.state,
                "ready": result.ready(),
                "successful": result.successful() if result.ready() else None,
                "failed": result.failed() if result.ready() else None,
            }
            
            # Add result or error info
            if result.ready():
                if result.successful():
                    status["result"] = result.result
                elif result.failed():
                    status["error"] = str(result.info)
                    status["traceback"] = result.traceback
            else:
                # Task is still pending/running
                status["info"] = result.info
                
            return status
            
        except Exception as e:
            logger.error(f"Error getting task status for {task_id}: {e}")
            return {
                "task_id": task_id,
                "error": str(e),
                "message": "Failed to get task status"
            }
    
    def list_active_tasks(self, worker_name: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        List active tasks across workers.
        
        Args:
            worker_name: Optional specific worker to query
            
        Returns:
            Dictionary mapping worker names to their active tasks
        """
        try:
            # Get active tasks from all workers
            inspect = self.app.control.inspect()
            active_tasks = inspect.active()
            
            if not active_tasks:
                return {}
            
            # Filter by worker if specified
            if worker_name and worker_name in active_tasks:
                return {worker_name: active_tasks[worker_name]}
            
            return active_tasks
            
        except Exception as e:
            logger.error(f"Error listing active tasks: {e}")
            return {}
    
    def list_scheduled_tasks(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        List scheduled tasks (in queue but not yet picked up by workers).
        
        Returns:
            Dictionary mapping worker names to their scheduled tasks
        """
        try:
            inspect = self.app.control.inspect()
            scheduled = inspect.scheduled()
            return scheduled or {}
            
        except Exception as e:
            logger.error(f"Error listing scheduled tasks: {e}")
            return {}
    
    def get_queue_size(self, queue_name: str = 'celery') -> int:
        """
        Get the size of a specific queue.
        
        Args:
            queue_name: Name of the queue to check
            
        Returns:
            Number of tasks in the queue
        """
        try:
            # This requires Redis backend
            if hasattr(self.app, 'backend') and hasattr(self.app.backend, 'client'):
                client = self.app.backend.client
                queue_key = f"celery-queue-{queue_name}"
                return client.llen(queue_key)
            else:
                logger.warning("Queue size check requires Redis backend")
                return -1
                
        except Exception as e:
            logger.error(f"Error getting queue size: {e}")
            return -1