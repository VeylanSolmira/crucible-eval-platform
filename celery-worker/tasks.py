"""
Celery tasks for code evaluation.

This module defines the core Celery tasks that process evaluation requests.
It integrates with the executor service for code execution and the storage
service for persistence.
"""

import os
import logging
from celery import Celery, signature
import httpx
from typing import Dict, Any, Optional
import redis
import traceback
from retry_config import get_retry_message, calculate_retry_delay, RETRYABLE_HTTP_CODES
from dlq_config import DeadLetterQueue
from executor_pool import ExecutorPool

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create Celery app
app = Celery("crucible_worker")
app.config_from_object("celeryconfig")

# Service URLs
STORAGE_SERVICE_URL = os.environ.get("STORAGE_SERVICE_URL", "http://storage-service:8082")
EXECUTOR_SERVICE_URL = os.environ.get("EXECUTOR_SERVICE_URL", None)

# Redis connection for DLQ and executor pool
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
redis_client = redis.from_url(REDIS_URL)
dlq = DeadLetterQueue(redis_client)

# Initialize executor pool
executor_pool = ExecutorPool(redis_client)

# Initialize pool with available executors on startup
# This should ideally be done by a separate initialization script
EXECUTOR_COUNT = int(os.environ.get("EXECUTOR_COUNT", "3"))
EXECUTOR_BASE_URL = os.environ.get("EXECUTOR_BASE_URL", "http://executor")
executor_urls = [f"{EXECUTOR_BASE_URL}-{i+1}:8083" for i in range(EXECUTOR_COUNT)]

# Import executor routing only if not using fixed executor
if not EXECUTOR_SERVICE_URL:
    from executor_router import get_executor_url, get_available_executor_url
    # Initialize the pool on worker startup
    try:
        executor_pool.initialize_pool(executor_urls)
        logger.info(f"Initialized executor pool with {len(executor_urls)} executors")
    except Exception as e:
        logger.error(f"Failed to initialize executor pool: {e}")


@app.task(bind=True, max_retries=30, result_expires=300)
def assign_executor(self, eval_id: str, code: str, language: str = "python") -> Dict[str, Any]:
    """
    Lightweight task that finds an available executor and chains to evaluation.
    This task can retry many times without issues since it does minimal work.
    
    Args:
        eval_id: Unique evaluation identifier
        code: Code to execute
        language: Programming language
        
    Returns:
        Task assignment result
    """
    logger.info(f"Assigning executor for evaluation {eval_id} (attempt {self.request.retries + 1})")
    
    try:
        # Store assigner task ID for potential cancellation
        redis_client.setex(f"assigner:{eval_id}", 300, self.request.id)
        
        # Try to claim an executor atomically
        executor_url = executor_pool.claim_executor(eval_id, ttl=600)  # 10 min TTL
        
        if not executor_url:
            # No executor available, retry with exponential backoff
            retry_count = self.request.retries
            if retry_count >= self.max_retries:
                # Max retries exhausted
                logger.error(f"No executor available for {eval_id} after {retry_count} attempts")
                # Update status to failed
                try:
                    with httpx.Client() as client:
                        client.put(
                            f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}",
                            json={
                                "status": "failed",
                                "error": f"No executor available after {retry_count} attempts"
                            }
                        )
                except Exception as e:
                    logger.error(f"Failed to update status for {eval_id}: {e}")
                
                return {
                    "eval_id": eval_id,
                    "status": "failed", 
                    "error": "No executor available",
                    "attempts": retry_count
                }
            
            # Calculate backoff delay (5s, 10s, 15s, ... max 30s)
            countdown = min(5 * (retry_count + 1), 30)
            logger.info(f"No executor available for {eval_id}, retrying in {countdown}s")
            raise self.retry(countdown=countdown)
        
        # Executor claimed! Clean up assigner tracking
        redis_client.delete(f"assigner:{eval_id}")
        
        logger.info(f"Assigned executor {executor_url} to evaluation {eval_id}")
        
        # Create the evaluation task with the assigned executor
        eval_task = evaluate_code.si(
            eval_id=eval_id,
            code=code, 
            language=language,
            executor_url=executor_url
        )
        
        # Create cleanup task that always runs after evaluation
        cleanup_task = release_executor_task.si(executor_url)
        
        # Chain: evaluation -> cleanup (on success)
        # Link error: cleanup (on failure)
        eval_task.link(cleanup_task)
        eval_task.link_error(cleanup_task)
        
        # Start the evaluation chain
        result = eval_task.apply_async()
        
        return {
            "eval_id": eval_id,
            "status": "assigned",
            "executor": executor_url,
            "task_id": result.id,
            "message": f"Evaluation assigned to {executor_url}"
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in assign_executor for {eval_id}: {e}")
        # Clean up assigner tracking
        redis_client.delete(f"assigner:{eval_id}")
        raise


@app.task
def release_executor_task(executor_url: str) -> Dict[str, Any]:
    """
    Cleanup task that releases an executor back to the pool.
    This always runs after evaluation (success or failure).
    
    Args:
        executor_url: URL of the executor to release
        
    Returns:
        Release status
    """
    try:
        executor_pool.release_executor(executor_url)
        logger.info(f"Released executor {executor_url} back to pool")
        return {"status": "released", "executor": executor_url}
    except Exception as e:
        logger.error(f"Failed to release executor {executor_url}: {e}")
        return {"status": "error", "executor": executor_url, "error": str(e)}


@app.task(
    bind=True,
    max_retries=5,
    autoretry_for=(httpx.HTTPError, httpx.ConnectTimeout, httpx.ReadTimeout),
    retry_kwargs={"max_retries": 5},
    retry_backoff=True,
    retry_backoff_max=600,  # Max 10 minutes between retries
    retry_jitter=True,  # Add randomness to prevent thundering herd
)
def evaluate_code(self, eval_id: str, code: str, language: str = "python", executor_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Main task for evaluating code submissions.

    Args:
        eval_id: Unique evaluation identifier
        code: Code to execute
        language: Programming language (currently only python)
        executor_url: Pre-assigned executor URL (from task chaining)

    Returns:
        Evaluation result dictionary
    """
    logger.info(f"Starting evaluation {eval_id} with executor_url={executor_url}")

    try:
        # Check if executor_url was provided (from task chaining)
        if executor_url:
            # Use the pre-assigned executor
            logger.info(f"Using pre-assigned executor: {executor_url}")
        elif EXECUTOR_SERVICE_URL:
            # Use fixed executor URL
            executor_url = EXECUTOR_SERVICE_URL
            logger.info(f"Using fixed executor: {executor_url}")
        else:
            # Legacy path: find available executor (should not be reached with task chaining)
            logger.warning(f"evaluate_code called without executor_url for {eval_id} - using legacy path")
            executor_url = get_available_executor_url()
            if not executor_url:
                # No executor available, retry the task
                logger.info(f"No executor available for {eval_id}, retrying in 5 seconds")
                raise self.retry(countdown=5, max_retries=None)  # Keep retrying until executor available
            logger.info(f"Found available executor for {eval_id}: {executor_url}")

        # Now that we have an executor, update status to provisioning
        with httpx.Client() as client:
            storage_response = client.put(
                f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}", json={"status": "provisioning"}
            )
            storage_response.raise_for_status()

        with httpx.Client(timeout=300.0) as client:  # 5 minute timeout
            execution_response = client.post(
                f"{executor_url}/execute",
                json={"eval_id": eval_id, "code": code, "language": language},
            )
            execution_response.raise_for_status()
            result = execution_response.json()

        # Update storage with the executor's response
        # The executor will publish evaluation:running event when container actually starts
        with httpx.Client() as client:
            storage_response = client.put(
                f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}",
                json={
                    "status": result.get("status", "provisioning"),  # Keep provisioning until executor says otherwise
                    "output": result.get("output", ""),
                    "error": result.get("error", ""),
                    "executor_id": result.get("executor_id", ""),
                    "container_id": result.get("container_id", ""),
                },
            )
            storage_response.raise_for_status()

        logger.info(f"Started evaluation {eval_id} on executor {result.get('executor_id')}")
        return result

    except httpx.HTTPError as e:
        # Categorize HTTP errors for smart retry logic
        if hasattr(e, "response") and e.response:
            status_code = e.response.status_code

            # Don't retry client errors (4xx) except specific ones
            if 400 <= status_code < 500:
                if status_code in [408, 429]:  # Timeout or rate limit
                    retry_count = self.request.retries
                    delay = calculate_retry_delay(
                        retry_count, "aggressive" if status_code == 429 else "default"
                    )

                    message = get_retry_message(
                        "evaluate_code",
                        eval_id,
                        retry_count,
                        self.max_retries,
                        delay,
                        f"HTTP {status_code}",
                    )
                    logger.warning(message)
                    raise self.retry(exc=e, countdown=delay)
                else:
                    # Don't retry other 4xx errors
                    logger.error(
                        f"Non-retryable client error for evaluation {eval_id}: {status_code}"
                    )
                    raise

            # Always retry server errors (5xx) with exponential backoff
            elif status_code >= 500:
                retry_count = self.request.retries
                delay = calculate_retry_delay(retry_count, "default")

                message = get_retry_message(
                    "evaluate_code",
                    eval_id,
                    retry_count,
                    self.max_retries,
                    delay,
                    f"HTTP {status_code} - {RETRYABLE_HTTP_CODES.get(status_code, 'Server Error')}",
                )
                logger.error(message)
                raise self.retry(exc=e, countdown=delay)

        # For connection errors, use exponential backoff
        retry_count = self.request.retries
        delay = calculate_retry_delay(retry_count, "default")

        message = get_retry_message(
            "evaluate_code",
            eval_id,
            retry_count,
            self.max_retries,
            delay,
            f"Connection error: {str(e)}",
        )
        logger.error(message)
        raise self.retry(exc=e, countdown=delay)
    except Exception as e:
        logger.error(f"Unexpected error during evaluation {eval_id}: {e}")

        # Check if we've exhausted retries
        if self.request.retries >= self.max_retries:
            # Add to Dead Letter Queue
            try:
                dlq.add_task(
                    task_id=self.request.id,
                    task_name="evaluate_code",
                    eval_id=eval_id,
                    args=[eval_id, code, language],
                    kwargs={},
                    exception=e,
                    traceback=traceback.format_exc(),
                    retry_count=self.request.retries,
                    metadata={
                        "code_preview": code[:100] if len(code) > 100 else code,
                        "language": language,
                        "storage_url": STORAGE_SERVICE_URL,
                    },
                )
                logger.warning(
                    f"Task {self.request.id} added to DLQ after {self.request.retries} retries"
                )
            except Exception as dlq_error:
                logger.error(f"Failed to add task to DLQ: {dlq_error}")

        # Update storage with error status
        try:
            with httpx.Client() as client:
                # Only mark as failed if we've exhausted retries
                is_final_failure = self.request.retries >= self.max_retries
                update_data = {
                    "error": str(e),
                    "retries": self.request.retries,
                    "retry_message": f"Retry {self.request.retries + 1}/{self.max_retries} in {calculate_retry_delay(self.request.retries)}s" if not is_final_failure else None,
                }
                
                # Only set status to failed on final failure
                if is_final_failure:
                    update_data["status"] = "failed"
                    update_data["final_failure"] = True
                
                client.put(
                    f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}",
                    json=update_data,
                )
        except Exception:
            pass  # Best effort storage update

        # Re-raise to let Celery handle retry logic
        raise


@app.task
def cleanup_old_evaluations():
    """
    Scheduled task to cleanup old evaluation data.
    Runs hourly via Celery Beat.
    """
    logger.info("Starting cleanup of old evaluations")

    try:
        with httpx.Client() as client:
            response = client.post(
                f"{STORAGE_SERVICE_URL}/maintenance/cleanup", json={"older_than_hours": 24}
            )
            response.raise_for_status()
            result = response.json()

        logger.info(f"Cleanup completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise


@app.task
def monitor_dead_letter_queue():
    """
    Scheduled task to monitor DLQ and alert on issues.
    Runs every 30 minutes via Celery Beat.
    """
    logger.info("Checking Dead Letter Queue status")

    try:
        stats = dlq.get_statistics()

        # Log statistics
        logger.info(f"DLQ Statistics: {stats}")

        # Alert if queue is growing
        if stats["queue_size"] > 100:
            logger.warning(f"DLQ size is {stats['queue_size']} - investigation needed")

            # Could send alerts here (email, Slack, PagerDuty, etc.)
            # alert_ops_team(f"DLQ has {stats['queue_size']} failed tasks")

        # Check for specific error patterns
        if stats.get("exception_breakdown"):
            for exc_type, count in stats["exception_breakdown"].items():
                if count > 10:
                    logger.warning(f"High frequency of {exc_type}: {count} occurrences")

        return stats

    except Exception as e:
        logger.error(f"Failed to monitor DLQ: {e}")
        raise


@app.task
def health_check():
    """Simple health check task for monitoring."""
    return {"status": "healthy", "worker": os.environ.get("HOSTNAME", "unknown")}
