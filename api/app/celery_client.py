"""
Celery client for submitting tasks from the API service.

This module provides a lightweight Celery client that can submit tasks
without importing the full worker codebase.
"""

import os
import logging
from typing import Optional
from celery import Celery
import redis
from .constants import TASK_MAPPING_TTL_SECONDS

logger = logging.getLogger(__name__)

# Celery configuration
CELERY_ENABLED = os.environ.get("CELERY_ENABLED", "false").lower() == "true"
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://celery-redis:6379/0")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

# Redis client for task ID mappings
redis_client = None
if CELERY_ENABLED:
    try:
        redis_client = redis.from_url(REDIS_URL)
        redis_client.ping()
        logger.info("Redis client initialized for task mappings")
    except Exception as e:
        logger.error(f"Failed to connect to Redis for mappings: {e}")
        redis_client = None

# Create minimal Celery app for task submission only
celery_app = None
if CELERY_ENABLED:
    try:
        celery_app = Celery("crucible_api", broker=CELERY_BROKER_URL)
        # Configure to match worker settings
        celery_app.conf.update(
            task_serializer="json",
            result_serializer="json",
            accept_content=["json"],
            task_track_started=True,
        )
        logger.info("Celery client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Celery client: {e}")
        CELERY_ENABLED = False


def submit_evaluation_to_celery(
    eval_id: str, code: str, language: str = "python", priority: bool = False
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
        # Use the new task chaining approach: assign_executor chains to evaluate_code
        # This allows proper retry handling without Redis limitations
        task_name = "tasks.assign_executor"
        queue = "high_priority" if priority else "evaluation"

        result = celery_app.send_task(
            task_name,
            args=[eval_id, code, language],
            queue=queue,
            # Let Celery auto-generate unique task IDs to support retries
        )
        
        task_id = result.id
        
        # Store bidirectional mapping between eval_id and task_id
        if redis_client:
            try:
                # TTL from constants - configurable for longer evaluations
                ttl = TASK_MAPPING_TTL_SECONDS
                # eval_id -> task_id (for cancellation/status checks)
                redis_client.setex(f"task_mapping:{eval_id}", ttl, task_id)
                # task_id -> eval_id (for reverse lookups if needed)
                redis_client.setex(f"eval_mapping:{task_id}", ttl, eval_id)
                logger.debug(f"Stored mapping: {eval_id} <-> {task_id}")
            except Exception as e:
                # Log but don't fail - the task will still run
                logger.error(f"Failed to store task mapping: {e}")

        logger.info(
            f"Submitted evaluation {eval_id} to Celery queue '{queue}', assigner_task_id: {task_id}"
        )
        logger.debug(
            f"Task will chain: assign_executor -> evaluate_code -> release_executor"
        )
        return task_id

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
            "broker_url": CELERY_BROKER_URL,
        }
    except Exception as e:
        return {"enabled": True, "connected": False, "error": str(e)}


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
        return {"cancelled": False, "reason": "Celery not enabled"}

    try:
        # Look up the actual task ID from our mapping
        task_id = None
        assigner_task_id = None
        if redis_client:
            try:
                # First check for the main task mapping
                task_id = redis_client.get(f"task_mapping:{eval_id}")
                if task_id:
                    task_id = task_id.decode('utf-8')
                
                # Also check for assigner task (if still in assignment phase)
                assigner_task_id = redis_client.get(f"assigner:{eval_id}")
                if assigner_task_id:
                    assigner_task_id = assigner_task_id.decode('utf-8')
            except Exception as e:
                logger.error(f"Failed to look up task mapping for {eval_id}: {e}")
        
        # If we have an assigner task, cancel it first
        if assigner_task_id:
            try:
                from celery.result import AsyncResult
                assigner_result = AsyncResult(assigner_task_id, app=celery_app)
                assigner_result.revoke()
                logger.info(f"Cancelled assigner task {assigner_task_id} for {eval_id}")
            except Exception as e:
                logger.error(f"Failed to cancel assigner task: {e}")
        
        if not task_id:
            if assigner_task_id:
                return {
                    "cancelled": True, 
                    "reason": "Cancelled during assignment phase", 
                    "message": f"Cancelled assigner task for evaluation {eval_id}"
                }
            return {
                "cancelled": False, 
                "reason": "Task not found", 
                "message": f"No Celery task found for evaluation {eval_id}"
            }

        # Get task result to check state
        from celery.result import AsyncResult

        result = AsyncResult(task_id, app=celery_app)

        response = {
            "eval_id": eval_id,
            "task_id": task_id,
            "previous_state": result.state,
            "cancelled": False,
            "message": "",
        }

        # Handle different states
        if result.state == "PENDING":
            # Task is in queue, can be cancelled
            result.revoke()
            response["cancelled"] = True
            response["message"] = "Task cancelled successfully (was pending in queue)"
            logger.info(f"Cancelled pending task {task_id}")

        elif result.state in ["STARTED", "RETRY"]:
            # Task is running
            if terminate:
                result.revoke(terminate=True)
                response["cancelled"] = True
                response["message"] = "Task forcefully terminated (was running)"
                logger.warning(f"Forcefully terminated task {task_id}")
            else:
                response["message"] = "Task is already running. Use terminate=true to force stop."

        elif result.state in ["SUCCESS", "FAILURE"]:
            response["message"] = f"Task already completed with state: {result.state}"

        elif result.state == "REVOKED":
            response["message"] = "Task was already cancelled"

        else:
            response["message"] = f"Unknown task state: {result.state}"

        return response

    except Exception as e:
        logger.error(f"Failed to cancel Celery task for {eval_id}: {e}")
        return {"cancelled": False, "error": str(e), "message": "Failed to cancel task"}


def get_celery_task_info(eval_id: str) -> dict:
    """
    Get detailed information about a Celery task.

    Args:
        eval_id: Evaluation ID

    Returns:
        Dict with task information
    """
    if not CELERY_ENABLED or not celery_app:
        return {"error": "Celery not enabled"}

    try:
        # Look up the actual task ID from our mapping
        task_id = None
        if redis_client:
            try:
                task_id = redis_client.get(f"task_mapping:{eval_id}")
                if task_id:
                    task_id = task_id.decode('utf-8')
            except Exception as e:
                logger.error(f"Failed to look up task mapping for {eval_id}: {e}")
        
        if not task_id:
            return {
                "error": "Task not found",
                "message": f"No Celery task found for evaluation {eval_id}"
            }

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
        return {"error": str(e)}
