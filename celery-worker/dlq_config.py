"""
Dead Letter Queue configuration for Celery.

This module handles tasks that have permanently failed after all retry attempts.
DLQ allows us to:
1. Analyze failure patterns
2. Manually retry with fixes
3. Alert on persistent issues
4. Prevent task loss
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import redis

logger = logging.getLogger(__name__)


@dataclass
class DeadLetterTask:
    """Represents a task in the dead letter queue."""

    task_id: str
    task_name: str
    eval_id: str
    args: List[Any]
    kwargs: Dict[str, Any]
    exception_class: str
    exception_message: str
    traceback: str
    retry_count: int
    first_failure_time: datetime
    last_failure_time: datetime
    metadata: Dict[str, Any]


class DeadLetterQueue:
    """Manages the dead letter queue for failed tasks."""

    def __init__(self, redis_client: redis.Redis, queue_name: str = "celery:dlq"):
        self.redis = redis_client
        self.queue_name = queue_name
        self.metadata_prefix = f"{queue_name}:metadata"

    def add_task(
        self,
        task_id: str,
        task_name: str,
        eval_id: str,
        args: List[Any],
        kwargs: Dict[str, Any],
        exception: Exception,
        traceback: str,
        retry_count: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Add a failed task to the dead letter queue.

        Returns:
            True if successfully added, False otherwise
        """
        try:
            # Create dead letter task
            dead_task = DeadLetterTask(
                task_id=task_id,
                task_name=task_name,
                eval_id=eval_id,
                args=args,
                kwargs=kwargs,
                exception_class=type(exception).__name__,
                exception_message=str(exception),
                traceback=traceback,
                retry_count=retry_count,
                first_failure_time=datetime.utcnow(),
                last_failure_time=datetime.utcnow(),
                metadata=metadata or {},
            )

            # Serialize task data
            task_data = json.dumps(asdict(dead_task), default=str)

            # Add to Redis list (FIFO queue)
            self.redis.rpush(self.queue_name, task_data)

            # Store metadata for quick lookup
            metadata_key = f"{self.metadata_prefix}:{task_id}"
            self.redis.hset(
                metadata_key,
                mapping={
                    "eval_id": eval_id,
                    "task_name": task_name,
                    "exception_class": dead_task.exception_class,
                    "retry_count": str(retry_count),
                    "added_at": dead_task.last_failure_time.isoformat(),
                },
            )

            # Set expiration (30 days by default)
            self.redis.expire(metadata_key, 30 * 24 * 60 * 60)

            logger.warning(
                f"Task {task_id} added to DLQ. "
                f"Eval: {eval_id}, Retries: {retry_count}, "
                f"Error: {dead_task.exception_class}"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to add task {task_id} to DLQ: {e}")
            return False

    def get_task(self, task_id: str) -> Optional[DeadLetterTask]:
        """Retrieve a specific task from the DLQ."""
        try:
            # Search through the queue
            queue_length = self.redis.llen(self.queue_name)

            for i in range(queue_length):
                task_data = self.redis.lindex(self.queue_name, i)
                if task_data:
                    task_dict = json.loads(task_data)
                    if task_dict.get("task_id") == task_id:
                        # Convert back to DeadLetterTask
                        task_dict["first_failure_time"] = datetime.fromisoformat(
                            task_dict["first_failure_time"]
                        )
                        task_dict["last_failure_time"] = datetime.fromisoformat(
                            task_dict["last_failure_time"]
                        )
                        return DeadLetterTask(**task_dict)

            return None

        except Exception as e:
            logger.error(f"Failed to retrieve task {task_id} from DLQ: {e}")
            return None

    def list_tasks(
        self, limit: int = 100, offset: int = 0, eval_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List tasks in the dead letter queue.

        Args:
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip
            eval_id: Filter by evaluation ID

        Returns:
            List of task metadata dictionaries
        """
        try:
            tasks = []

            # Get range from queue
            if eval_id:
                # Filter by eval_id using metadata
                pattern = f"{self.metadata_prefix}:*"
                cursor = 0

                while len(tasks) < limit:
                    cursor, keys = self.redis.scan(cursor, match=pattern, count=100)

                    for key in keys:
                        metadata = self.redis.hgetall(key)
                        if metadata.get(b"eval_id", b"").decode() == eval_id:
                            task_id = key.decode().split(":")[-1]
                            tasks.append(
                                {
                                    "task_id": task_id,
                                    "eval_id": eval_id,
                                    "task_name": metadata.get(b"task_name", b"").decode(),
                                    "exception_class": metadata.get(
                                        b"exception_class", b""
                                    ).decode(),
                                    "retry_count": int(metadata.get(b"retry_count", b"0")),
                                    "added_at": metadata.get(b"added_at", b"").decode(),
                                }
                            )

                    if cursor == 0:
                        break
            else:
                # Get all tasks
                start = offset
                end = offset + limit - 1
                task_items = self.redis.lrange(self.queue_name, start, end)

                for task_data in task_items:
                    if task_data:
                        task_dict = json.loads(task_data)
                        tasks.append(
                            {
                                "task_id": task_dict["task_id"],
                                "eval_id": task_dict["eval_id"],
                                "task_name": task_dict["task_name"],
                                "exception_class": task_dict["exception_class"],
                                "retry_count": task_dict["retry_count"],
                                "added_at": task_dict["last_failure_time"],
                            }
                        )

            return tasks[:limit]

        except Exception as e:
            logger.error(f"Failed to list DLQ tasks: {e}")
            return []

    def retry_task(self, task_id: str) -> bool:
        """
        Retry a task from the dead letter queue.

        This removes the task from DLQ and resubmits it.
        """
        try:
            # Find and remove the task
            task = self.get_task(task_id)
            if not task:
                logger.error(f"Task {task_id} not found in DLQ")
                return False

            # Remove from queue
            queue_length = self.redis.llen(self.queue_name)
            for i in range(queue_length):
                task_data = self.redis.lindex(self.queue_name, i)
                if task_data:
                    task_dict = json.loads(task_data)
                    if task_dict.get("task_id") == task_id:
                        # Remove this item
                        self.redis.lrem(self.queue_name, 1, task_data)
                        break

            # Remove metadata
            metadata_key = f"{self.metadata_prefix}:{task_id}"
            self.redis.delete(metadata_key)

            # Resubmit the task
            from celery import current_app

            current_app.send_task(
                task.task_name, args=task.args, kwargs=task.kwargs, task_id=task_id
            )

            logger.info(f"Task {task_id} resubmitted from DLQ")
            return True

        except Exception as e:
            logger.error(f"Failed to retry task {task_id} from DLQ: {e}")
            return False

    def remove_task(self, task_id: str) -> bool:
        """Permanently remove a task from the DLQ."""
        try:
            # Find and remove the task
            queue_length = self.redis.llen(self.queue_name)
            removed = False

            for i in range(queue_length):
                task_data = self.redis.lindex(self.queue_name, i)
                if task_data:
                    task_dict = json.loads(task_data)
                    if task_dict.get("task_id") == task_id:
                        # Remove this item
                        self.redis.lrem(self.queue_name, 1, task_data)
                        removed = True
                        break

            # Remove metadata
            metadata_key = f"{self.metadata_prefix}:{task_id}"
            self.redis.delete(metadata_key)

            if removed:
                logger.info(f"Task {task_id} removed from DLQ")

            return removed

        except Exception as e:
            logger.error(f"Failed to remove task {task_id} from DLQ: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the dead letter queue."""
        try:
            queue_size = self.redis.llen(self.queue_name)

            # Get exception breakdown
            exception_counts = {}
            task_name_counts = {}

            # Sample first 1000 tasks for statistics
            sample_size = min(queue_size, 1000)
            tasks = self.redis.lrange(self.queue_name, 0, sample_size - 1)

            for task_data in tasks:
                if task_data:
                    task_dict = json.loads(task_data)
                    exc_class = task_dict.get("exception_class", "Unknown")
                    task_name = task_dict.get("task_name", "Unknown")

                    exception_counts[exc_class] = exception_counts.get(exc_class, 0) + 1
                    task_name_counts[task_name] = task_name_counts.get(task_name, 0) + 1

            return {
                "queue_size": queue_size,
                "exception_breakdown": exception_counts,
                "task_breakdown": task_name_counts,
                "sample_size": sample_size,
            }

        except Exception as e:
            logger.error(f"Failed to get DLQ statistics: {e}")
            return {"queue_size": 0, "error": str(e)}
