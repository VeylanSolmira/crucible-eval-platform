"""
Celery tasks for code evaluation.

This module defines the core Celery tasks that process evaluation requests.
It integrates with the executor service for code execution and the storage
service for persistence.
"""

import os
import logging
from celery import signature
import httpx
from typing import Dict, Any, Optional
import redis
import traceback
from celery_worker.retry_config import get_retry_message, calculate_retry_delay, RETRYABLE_HTTP_CODES
from celery_worker.dlq_config import DeadLetterQueue

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import the Celery app instance
from celery_worker.celery_app import app

# Service URLs
STORAGE_SERVICE_URL = os.environ.get("STORAGE_SERVICE_URL", "http://storage-service:8082")
DISPATCHER_SERVICE_URL = os.environ.get("DISPATCHER_SERVICE_URL", "http://dispatcher-service:8090")

# Import resilient connection utilities
from shared.utils.resilient_connections import get_redis_client

# Redis connection for DLQ with retry logic
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
redis_client = get_redis_client(REDIS_URL)
dlq = DeadLetterQueue(redis_client)




@app.task(
    bind=True,
    max_retries=5,
    autoretry_for=(httpx.HTTPError, httpx.ConnectTimeout, httpx.ReadTimeout),
    retry_kwargs={"max_retries": 5},
    retry_backoff=True,
    retry_backoff_max=600,  # Max 10 minutes between retries
    retry_jitter=True,  # Add randomness to prevent thundering herd
)
def evaluate_code(self, eval_id: str, code: str, language: str = "python", timeout: int = 300, priority: int = 0, executor_image: Optional[str] = None, memory_limit: str = "512Mi", cpu_limit: str = "500m") -> Dict[str, Any]:
    """
    Main task for evaluating code submissions using the dispatcher service.

    Args:
        eval_id: Unique evaluation identifier
        code: Code to execute
        language: Programming language (currently only python)
        timeout: Execution timeout in seconds (default: 300)
        priority: Priority level (0=normal, 1=high, -1=low) (default: 0)
        executor_image: Executor image name (e.g., 'executor-base') or full image path
        memory_limit: Memory limit for the evaluation (e.g., '512Mi', '1Gi') (default: 512Mi)
        cpu_limit: CPU limit for the evaluation (e.g., '500m', '1') (default: 500m)

    Returns:
        Evaluation result dictionary
    """
    logger.info(f"Starting evaluation {eval_id} via dispatcher with timeout={timeout}s")

    try:
        # Update status to provisioning
        with httpx.Client() as client:
            storage_response = client.put(
                f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}", json={"status": "provisioning"}
            )
            storage_response.raise_for_status()

        # Check cluster capacity before attempting to create job
        # Use the resource limits passed from the API
        
        with httpx.Client(timeout=30.0) as client:
            # Check capacity first
            capacity_response = client.post(
                f"{DISPATCHER_SERVICE_URL}/capacity/check",
                json={
                    "memory_limit": memory_limit,
                    "cpu_limit": cpu_limit
                }
            )
            
            if capacity_response.status_code == 200:
                capacity_data = capacity_response.json()
                if not capacity_data.get("has_capacity", False):
                    # No capacity available - this is a temporary condition, retry
                    retry_count = self.request.retries
                    max_retries = 10  # Same as quota_exceeded policy
                    
                    # Check if we've exceeded retry limit
                    if retry_count >= max_retries:
                        error_msg = (
                            f"Evaluation {eval_id} failed after {retry_count} capacity retries. "
                            f"Cluster resources exhausted. Final state: "
                            f"{capacity_data.get('available_memory_mb')}MB memory, "
                            f"{capacity_data.get('available_cpu_millicores')}m CPU available"
                        )
                        logger.error(error_msg)
                        # Update storage to mark as failed
                        with httpx.Client() as storage_client:
                            storage_client.put(
                                f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}",
                                json={
                                    "status": "failed",
                                    "error": error_msg,
                                    "metadata": {"reason": "resource_exhaustion"}
                                }
                            )
                        # Return failure instead of proceeding
                        return {
                            "eval_id": eval_id,
                            "status": "failed",
                            "error": error_msg
                        }
                    else:
                        logger.info(
                            f"No cluster capacity for eval {eval_id}: {capacity_data.get('reason')}. "
                            f"Available: {capacity_data.get('available_memory_mb')}MB memory, "
                            f"{capacity_data.get('available_cpu_millicores')}m CPU. "
                            f"Retry {retry_count + 1}/{max_retries}"
                        )
                        delay = calculate_retry_delay(retry_count, "quota_exceeded")
                        raise self.retry(countdown=delay)
            
            # Capacity available (or check failed), proceed with job creation
            dispatch_response = client.post(
                f"{DISPATCHER_SERVICE_URL}/execute",
                json={
                    "eval_id": eval_id,
                    "code": code,
                    "language": language,
                    "timeout": timeout,  # Use the actual timeout from the request
                    "memory_limit": memory_limit,
                    "cpu_limit": cpu_limit,
                    "priority": priority,  # Pass priority to dispatcher
                    "executor_image": executor_image  # Pass executor image to dispatcher
                }
            )
            dispatch_response.raise_for_status()
            result = dispatch_response.json()

        logger.info(f"Created job {result.get('job_name')} for evaluation {eval_id}")
        
        # Store job name for monitoring
        redis_client.setex(f"eval:{eval_id}:job", 3600, result.get('job_name', ''))
        
        # Update storage with job creation info
        with httpx.Client() as client:
            storage_response = client.put(
                f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}",
                json={
                    "status": "provisioning",
                    "metadata": {
                        "job_name": result.get('job_name'),
                        "namespace": result.get('namespace', 'crucible')
                    }
                }
            )
            storage_response.raise_for_status()

        # Check if event monitoring is enabled in dispatcher
        # If it is, we don't need to poll from Celery
        event_monitoring_enabled = os.getenv("ENABLE_EVENT_MONITORING", "true").lower() == "true"
        
        if not event_monitoring_enabled:
            # Start monitoring the job only if event monitoring is disabled
            job_name_from_dispatcher = result.get('job_name')
            if not job_name_from_dispatcher:
                logger.error(f"No job_name in dispatcher response for eval {eval_id}: {result}")
                raise ValueError(f"Dispatcher did not return job_name for evaluation {eval_id}")
            
            logger.info(f"Starting monitor for eval {eval_id} with job_name {job_name_from_dispatcher}")
            monitor_job_status.delay(eval_id, job_name_from_dispatcher)
        else:
            logger.info(f"Event monitoring enabled - skipping Celery polling for eval {eval_id}")
        
        return result

    except httpx.HTTPError as e:
        # Categorize HTTP errors for smart retry logic
        if hasattr(e, "response") and e.response:
            status_code = e.response.status_code

            # Don't retry client errors (4xx) except specific ones
            if 400 <= status_code < 500:
                if status_code in [408, 429]:  # Timeout or rate limit
                    retry_count = self.request.retries
                    
                    if status_code == 429:
                        # For quota exceeded, use special policy with 10 retries
                        policy = "quota_exceeded"
                        max_retries = 10
                        
                        # Check if we've exceeded quota retry limit
                        if retry_count >= max_retries:
                            logger.error(
                                f"Evaluation {eval_id} failed after {retry_count} quota retries. "
                                "Cluster resources exhausted."
                            )
                            # Don't retry further - let it fail
                            raise
                    else:
                        policy = "default"
                        max_retries = self.max_retries
                    
                    delay = calculate_retry_delay(retry_count, policy)
                    message = get_retry_message(
                        "evaluate_code",
                        eval_id,
                        retry_count,
                        max_retries,
                        delay,
                        f"HTTP {status_code}",
                    )
                    logger.warning(message)
                    
                    # Retry with calculated delay
                    raise self.retry(exc=e, countdown=delay)
                else:
                    # Don't retry other 4xx errors
                    logger.error(
                        f"Non-retryable client error for evaluation {eval_id}: {status_code}"
                    )
                    
                    # Update evaluation status to failed
                    error_detail = "Unknown client error"
                    if hasattr(e.response, "text"):
                        try:
                            error_data = e.response.json()
                            error_detail = error_data.get("detail", e.response.text)
                        except:
                            error_detail = e.response.text
                    
                    # Update storage to mark as failed
                    with httpx.Client() as storage_client:
                        storage_client.put(
                            f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}",
                            json={
                                "status": "failed",
                                "error": f"Validation error: {error_detail}",
                                "metadata": {"reason": "validation_error", "status_code": status_code}
                            }
                        )
                    
                    # Don't retry - this is a permanent failure
                    return {
                        "eval_id": eval_id,
                        "status": "failed",
                        "error": f"Validation error: {error_detail}"
                    }

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
        max_retries = self.max_retries if self.max_retries is not None else 5
        if self.request.retries >= max_retries:
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
                max_retries = self.max_retries if self.max_retries is not None else 5
                is_final_failure = self.request.retries >= max_retries
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


@app.task(bind=True, max_retries=60)  # Retry for up to 10 minutes
def monitor_job_status(self, eval_id: str, job_name: str) -> Dict[str, Any]:
    """
    Monitor Kubernetes Job status and update evaluation accordingly.
    
    Args:
        eval_id: Evaluation ID
        job_name: Kubernetes Job name
        
    Returns:
        Job status information
    """
    logger.info(f"Monitor task started - eval_id: {eval_id}, job_name: {job_name}, job_name type: {type(job_name)}")
    
    # Defensive check
    if not job_name or job_name == eval_id:
        logger.error(f"Invalid job_name '{job_name}' for eval {eval_id} - expected format like '{eval_id}-job'")
    
    logger.info(f"Monitoring job {job_name} for evaluation {eval_id}")
    
    try:
        # Get job status from dispatcher
        with httpx.Client() as client:
            response = client.get(f"{DISPATCHER_SERVICE_URL}/status/{job_name}")
            response.raise_for_status()
            status_info = response.json()
        
        job_status = status_info.get('status', 'unknown')
        logger.info(f"Job {job_name} status: {job_status}")
        
        if job_status == 'succeeded':
            # Get logs from the job
            with httpx.Client() as client:
                logs_response = client.get(f"{DISPATCHER_SERVICE_URL}/logs/{job_name}")
                logs_response.raise_for_status()
                logs_data = logs_response.json()
            
            # Update evaluation as completed
            with httpx.Client() as client:
                storage_response = client.put(
                    f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}",
                    json={
                        "status": "completed",
                        "output": logs_data.get('logs', ''),
                        "exit_code": logs_data.get('exit_code', 0)
                    }
                )
                storage_response.raise_for_status()
            
            return {"status": "completed", "eval_id": eval_id}
            
        elif job_status == 'failed':
            # Get error information
            with httpx.Client() as client:
                logs_response = client.get(f"{DISPATCHER_SERVICE_URL}/logs/{job_name}")
                logs_data = logs_response.json() if logs_response.status_code == 200 else {}
            
            # Update evaluation as failed
            with httpx.Client() as client:
                storage_response = client.put(
                    f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}",
                    json={
                        "status": "failed",
                        "error": logs_data.get('logs', 'Job failed'),
                        "exit_code": logs_data.get('exit_code', 1)
                    }
                )
                storage_response.raise_for_status()
            
            return {"status": "failed", "eval_id": eval_id}
            
        elif job_status in ['pending', 'running']:
            # Update status if changed
            current_status = 'provisioning' if job_status == 'pending' else 'running'
            
            # Include executor info for running status
            update_data = {"status": current_status}
            if job_status == 'running':
                # Pass job_name as executor_id and container_id for storage-worker
                update_data["executor_id"] = job_name
                update_data["container_id"] = job_name
                update_data["timeout"] = 300  # Default timeout, could get from job spec
            
            with httpx.Client() as client:
                storage_response = client.put(
                    f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}",
                    json=update_data
                )
                storage_response.raise_for_status()
            
            # Retry in 10 seconds
            raise self.retry(countdown=10)
            
        else:
            # Unknown status, retry
            logger.warning(f"Unknown job status: {job_status}")
            raise self.retry(countdown=10)
            
    except httpx.HTTPError as e:
        logger.error(f"Error monitoring job {job_name}: {e}")
        max_retries = self.max_retries if self.max_retries is not None else 60
        if self.request.retries >= max_retries:
            # Mark evaluation as failed after too many retries
            try:
                with httpx.Client() as client:
                    client.put(
                        f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}",
                        json={
                            "status": "failed",
                            "error": f"Failed to monitor job: {str(e)}"
                        }
                    )
            except Exception:
                pass
        raise self.retry(exc=e, countdown=10)


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
