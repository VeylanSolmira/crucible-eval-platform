"""
Celery tasks for code evaluation.

This module defines the core Celery tasks that process evaluation requests.
It integrates with the executor service for code execution and the storage
service for persistence.
"""
import os
import logging
from celery import Celery
import httpx
from typing import Dict, Any
import redis
import traceback
from retry_config import get_retry_message, calculate_retry_delay, RETRYABLE_HTTP_CODES
from dlq_config import DeadLetterQueue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Celery app
app = Celery('crucible_worker')
app.config_from_object('celeryconfig')

# Service URLs
STORAGE_SERVICE_URL = os.environ.get('STORAGE_SERVICE_URL', 'http://storage-service:8082')
EXECUTOR_SERVICE_URL = os.environ.get('EXECUTOR_SERVICE_URL', None)

# Redis connection for DLQ
REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
redis_client = redis.from_url(REDIS_URL)
dlq = DeadLetterQueue(redis_client)

# Import executor routing only if not using fixed executor
if not EXECUTOR_SERVICE_URL:
    from executor_router import get_executor_url

@app.task(
    bind=True, 
    max_retries=5,
    autoretry_for=(httpx.HTTPError, httpx.ConnectTimeout, httpx.ReadTimeout),
    retry_kwargs={'max_retries': 5},
    retry_backoff=True,
    retry_backoff_max=600,  # Max 10 minutes between retries
    retry_jitter=True,      # Add randomness to prevent thundering herd
)
def evaluate_code(self, eval_id: str, code: str, language: str = "python") -> Dict[str, Any]:
    """
    Main task for evaluating code submissions.
    
    Args:
        eval_id: Unique evaluation identifier
        code: Code to execute
        language: Programming language (currently only python)
    
    Returns:
        Evaluation result dictionary
    """
    logger.info(f"Starting evaluation {eval_id}")
    
    try:
        # Update status to running
        with httpx.Client() as client:
            storage_response = client.put(
                f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}",
                json={"status": "running"}
            )
            storage_response.raise_for_status()
        
        # Execute code via executor service
        if EXECUTOR_SERVICE_URL:
            # Use fixed executor URL
            executor_url = EXECUTOR_SERVICE_URL
            logger.info(f"Using fixed executor: {executor_url}")
        else:
            # Use dynamic routing
            executor_url = get_executor_url()
            logger.info(f"Routing evaluation {eval_id} to {executor_url}")
        
        with httpx.Client(timeout=300.0) as client:  # 5 minute timeout
            execution_response = client.post(
                f"{executor_url}/execute",
                json={
                    "eval_id": eval_id,
                    "code": code,
                    "language": language
                }
            )
            execution_response.raise_for_status()
            result = execution_response.json()
        
        # Update storage with results
        with httpx.Client() as client:
            storage_response = client.put(
                f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}",
                json={
                    "status": "completed",
                    "output": result.get("output", ""),
                    "error": result.get("error", ""),
                    "execution_time": result.get("execution_time", 0)
                }
            )
            storage_response.raise_for_status()
        
        logger.info(f"Completed evaluation {eval_id}")
        return result
        
    except httpx.HTTPError as e:
        # Categorize HTTP errors for smart retry logic
        if hasattr(e, 'response') and e.response:
            status_code = e.response.status_code
            
            # Don't retry client errors (4xx) except specific ones
            if 400 <= status_code < 500:
                if status_code in [408, 429]:  # Timeout or rate limit
                    retry_count = self.request.retries
                    delay = calculate_retry_delay(retry_count, 'aggressive' if status_code == 429 else 'default')
                    
                    message = get_retry_message(
                        'evaluate_code', eval_id, retry_count, self.max_retries,
                        delay, f"HTTP {status_code}"
                    )
                    logger.warning(message)
                    raise self.retry(exc=e, countdown=delay)
                else:
                    # Don't retry other 4xx errors
                    logger.error(f"Non-retryable client error for evaluation {eval_id}: {status_code}")
                    raise
            
            # Always retry server errors (5xx) with exponential backoff
            elif status_code >= 500:
                retry_count = self.request.retries
                delay = calculate_retry_delay(retry_count, 'default')
                
                message = get_retry_message(
                    'evaluate_code', eval_id, retry_count, self.max_retries,
                    delay, f"HTTP {status_code} - {RETRYABLE_HTTP_CODES.get(status_code, 'Server Error')}"
                )
                logger.error(message)
                raise self.retry(exc=e, countdown=delay)
        
        # For connection errors, use exponential backoff
        retry_count = self.request.retries
        delay = calculate_retry_delay(retry_count, 'default')
        
        message = get_retry_message(
            'evaluate_code', eval_id, retry_count, self.max_retries,
            delay, f"Connection error: {str(e)}"
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
                    task_name='evaluate_code',
                    eval_id=eval_id,
                    args=[eval_id, code, language],
                    kwargs={},
                    exception=e,
                    traceback=traceback.format_exc(),
                    retry_count=self.request.retries,
                    metadata={
                        'code_preview': code[:100] if len(code) > 100 else code,
                        'language': language,
                        'storage_url': STORAGE_SERVICE_URL
                    }
                )
                logger.warning(f"Task {self.request.id} added to DLQ after {self.request.retries} retries")
            except Exception as dlq_error:
                logger.error(f"Failed to add task to DLQ: {dlq_error}")
        
        # Update storage with error status
        try:
            with httpx.Client() as client:
                client.put(
                    f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}",
                    json={
                        "status": "failed",
                        "error": str(e),
                        "retries": self.request.retries,
                        "final_failure": self.request.retries >= self.max_retries
                    }
                )
        except:
            pass  # Best effort
        
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
                f"{STORAGE_SERVICE_URL}/maintenance/cleanup",
                json={"older_than_hours": 24}
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
        if stats['queue_size'] > 100:
            logger.warning(f"DLQ size is {stats['queue_size']} - investigation needed")
            
            # Could send alerts here (email, Slack, PagerDuty, etc.)
            # alert_ops_team(f"DLQ has {stats['queue_size']} failed tasks")
        
        # Check for specific error patterns
        if stats.get('exception_breakdown'):
            for exc_type, count in stats['exception_breakdown'].items():
                if count > 10:
                    logger.warning(f"High frequency of {exc_type}: {count} occurrences")
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to monitor DLQ: {e}")
        raise

@app.task
def health_check():
    """Simple health check task for monitoring."""
    return {"status": "healthy", "worker": os.environ.get('HOSTNAME', 'unknown')}