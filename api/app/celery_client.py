"""
Celery client for submitting tasks from the API service.

This module provides a lightweight Celery client that can submit tasks
without importing the full worker codebase.
"""
import os
import logging
from typing import Optional
from celery import Celery

logger = logging.getLogger(__name__)

# Celery configuration
CELERY_ENABLED = os.environ.get('CELERY_ENABLED', 'false').lower() == 'true'
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://celery-redis:6379/0')

# Create minimal Celery app for task submission only
celery_app = None
if CELERY_ENABLED:
    try:
        celery_app = Celery('crucible_api', broker=CELERY_BROKER_URL)
        # Configure to match worker settings
        celery_app.conf.update(
            task_serializer='json',
            result_serializer='json',
            accept_content=['json'],
            task_track_started=True,
        )
        logger.info("Celery client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Celery client: {e}")
        CELERY_ENABLED = False

def submit_evaluation_to_celery(
    eval_id: str, 
    code: str, 
    language: str = "python",
    priority: bool = False
) -> Optional[str]:
    """
    Submit evaluation task to Celery if enabled.
    
    Args:
        eval_id: Evaluation ID
        code: Code to evaluate
        language: Programming language
        priority: Whether this is a high-priority task
        
    Returns:
        Celery task ID if submitted, None otherwise
    """
    if not CELERY_ENABLED or not celery_app:
        return None
    
    try:
        # Send task without importing the task function
        # This allows API to submit tasks without having worker code
        task_name = 'tasks.evaluate_code'
        queue = 'high_priority' if priority else 'evaluation'
        
        result = celery_app.send_task(
            task_name,
            args=[eval_id, code, language],
            queue=queue,
            task_id=f"celery-{eval_id}"  # Predictable task ID
        )
        
        logger.info(f"Submitted evaluation {eval_id} to Celery queue '{queue}', task_id: {result.id}")
        return result.id
        
    except Exception as e:
        logger.error(f"Failed to submit task to Celery: {e}")
        return None

def get_celery_status() -> dict:
    """Get Celery connection status for health checks."""
    if not CELERY_ENABLED:
        return {"enabled": False, "connected": False}
    
    try:
        # Try to inspect workers
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        return {
            "enabled": True,
            "connected": bool(stats),
            "workers": len(stats) if stats else 0,
            "broker_url": CELERY_BROKER_URL
        }
    except Exception as e:
        return {
            "enabled": True,
            "connected": False,
            "error": str(e)
        }

def cancel_celery_task(eval_id: str, terminate: bool = False) -> dict:
    """
    Cancel a Celery task.
    
    Args:
        eval_id: Evaluation ID
        terminate: If True, forcefully terminate running tasks
        
    Returns:
        Dict with cancellation status
    """
    if not CELERY_ENABLED or not celery_app:
        return {
            "cancelled": False,
            "reason": "Celery not enabled"
        }
    
    try:
        # Use predictable task ID format
        task_id = f"celery-{eval_id}"
        
        # Get task result to check state
        from celery.result import AsyncResult
        result = AsyncResult(task_id, app=celery_app)
        
        response = {
            "eval_id": eval_id,
            "task_id": task_id,
            "previous_state": result.state,
            "cancelled": False,
            "message": ""
        }
        
        # Handle different states
        if result.state == 'PENDING':
            # Task is in queue, can be cancelled
            result.revoke()
            response["cancelled"] = True
            response["message"] = "Task cancelled successfully (was pending in queue)"
            logger.info(f"Cancelled pending task {task_id}")
            
        elif result.state in ['STARTED', 'RETRY']:
            # Task is running
            if terminate:
                result.revoke(terminate=True)
                response["cancelled"] = True
                response["message"] = "Task forcefully terminated (was running)"
                logger.warning(f"Forcefully terminated task {task_id}")
            else:
                response["message"] = "Task is already running. Use terminate=true to force stop."
                
        elif result.state in ['SUCCESS', 'FAILURE']:
            response["message"] = f"Task already completed with state: {result.state}"
            
        elif result.state == 'REVOKED':
            response["message"] = "Task was already cancelled"
            
        else:
            response["message"] = f"Unknown task state: {result.state}"
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to cancel Celery task for {eval_id}: {e}")
        return {
            "cancelled": False,
            "error": str(e),
            "message": "Failed to cancel task"
        }

def get_celery_task_info(eval_id: str) -> dict:
    """
    Get detailed information about a Celery task.
    
    Args:
        eval_id: Evaluation ID
        
    Returns:
        Dict with task information
    """
    if not CELERY_ENABLED or not celery_app:
        return {
            "error": "Celery not enabled"
        }
    
    try:
        task_id = f"celery-{eval_id}"
        from celery.result import AsyncResult
        result = AsyncResult(task_id, app=celery_app)
        
        info = {
            "eval_id": eval_id,
            "task_id": task_id,
            "state": result.state,
            "ready": result.ready(),
        }
        
        if result.ready():
            info["successful"] = result.successful()
            info["failed"] = result.failed()
            
            if result.successful():
                info["result"] = result.result
            elif result.failed():
                info["error"] = str(result.info)
                info["traceback"] = result.traceback
        
        return info
        
    except Exception as e:
        logger.error(f"Failed to get Celery task info for {eval_id}: {e}")
        return {
            "error": str(e)
        }