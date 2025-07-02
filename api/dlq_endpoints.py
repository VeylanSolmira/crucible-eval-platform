"""
Dead Letter Queue API endpoints.

This module provides REST API endpoints for viewing and managing
tasks that have failed permanently and are stored in the DLQ.
"""

from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, Query
import redis
import logging
from pydantic import BaseModel

# Import DLQ from celery worker
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "celery-worker"))
from dlq_config import DeadLetterQueue

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/dlq", tags=["dead-letter-queue"])

# Redis connection
REDIS_URL = "redis://redis:6379/0"  # Should match Celery config
redis_client = redis.from_url(REDIS_URL)
dlq = DeadLetterQueue(redis_client)


class DLQTaskResponse(BaseModel):
    """Response model for DLQ task information."""

    task_id: str
    eval_id: str
    task_name: str
    exception_class: str
    retry_count: int
    added_at: str


class DLQStatisticsResponse(BaseModel):
    """Response model for DLQ statistics."""

    queue_size: int
    exception_breakdown: Dict[str, int]
    task_breakdown: Dict[str, int]
    sample_size: int


@router.get("/tasks", response_model=List[DLQTaskResponse])
async def list_dlq_tasks(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    eval_id: Optional[str] = None,
):
    """
    List tasks in the Dead Letter Queue.

    Args:
        limit: Maximum number of tasks to return
        offset: Number of tasks to skip
        eval_id: Filter by evaluation ID
    """
    try:
        tasks = dlq.list_tasks(limit=limit, offset=offset, eval_id=eval_id)
        return tasks
    except Exception as e:
        logger.error(f"Failed to list DLQ tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve DLQ tasks")


@router.get("/statistics", response_model=DLQStatisticsResponse)
async def get_dlq_statistics():
    """Get statistics about the Dead Letter Queue."""
    try:
        stats = dlq.get_statistics()
        return DLQStatisticsResponse(**stats)
    except Exception as e:
        logger.error(f"Failed to get DLQ statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve DLQ statistics")


@router.get("/tasks/{task_id}")
async def get_dlq_task(task_id: str):
    """Get detailed information about a specific DLQ task."""
    try:
        task = dlq.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found in DLQ")

        # Convert to dict for JSON response
        task_dict = {
            "task_id": task.task_id,
            "task_name": task.task_name,
            "eval_id": task.eval_id,
            "args": task.args,
            "kwargs": task.kwargs,
            "exception_class": task.exception_class,
            "exception_message": task.exception_message,
            "traceback": task.traceback,
            "retry_count": task.retry_count,
            "first_failure_time": task.first_failure_time.isoformat(),
            "last_failure_time": task.last_failure_time.isoformat(),
            "metadata": task.metadata,
        }

        return task_dict
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get DLQ task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve task")


@router.post("/tasks/{task_id}/retry")
async def retry_dlq_task(task_id: str):
    """
    Retry a task from the Dead Letter Queue.

    This removes the task from DLQ and resubmits it to Celery.
    """
    try:
        success = dlq.retry_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found or retry failed")

        return {
            "status": "success",
            "message": f"Task {task_id} resubmitted from DLQ",
            "task_id": task_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry DLQ task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retry task")


@router.delete("/tasks/{task_id}")
async def remove_dlq_task(task_id: str):
    """
    Permanently remove a task from the Dead Letter Queue.

    Use with caution - this permanently deletes the task information.
    """
    try:
        success = dlq.remove_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found in DLQ")

        return {"status": "success", "message": f"Task {task_id} removed from DLQ"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove DLQ task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove task")


@router.post("/tasks/retry-batch")
async def retry_dlq_tasks_batch(task_ids: List[str]):
    """
    Retry multiple tasks from the Dead Letter Queue.

    Args:
        task_ids: List of task IDs to retry
    """
    if not task_ids:
        raise HTTPException(status_code=400, detail="No task IDs provided")

    if len(task_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 tasks can be retried at once")

    results = {"succeeded": [], "failed": []}

    for task_id in task_ids:
        try:
            if dlq.retry_task(task_id):
                results["succeeded"].append(task_id)
            else:
                results["failed"].append({"task_id": task_id, "error": "Not found"})
        except Exception as e:
            results["failed"].append({"task_id": task_id, "error": str(e)})

    return {
        "total": len(task_ids),
        "succeeded": len(results["succeeded"]),
        "failed": len(results["failed"]),
        "results": results,
    }
