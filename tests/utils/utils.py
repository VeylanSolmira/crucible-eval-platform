"""Common utilities for integration tests"""

import time
import requests
import os
from typing import Dict, Any, Optional


# Get API URL from environment - must be explicitly set
API_URL = os.getenv("API_BASE_URL") or os.getenv("API_URL")
if not API_URL:
    raise ValueError(
        "API_URL or API_BASE_URL environment variable must be set. "
        "Example: API_URL=http://api-service.dev.svc.cluster.local:8080/api"
    )


def submit_evaluation(code: str, language: str = "python", timeout: int = 30, 
                     memory_limit: Optional[str] = None, cpu_limit: Optional[str] = None, 
                     executor_image: str = None, debug: bool = False, priority: int = -1) -> str:
    """Submit an evaluation to the API
    
    Args:
        code: Code to evaluate
        language: Programming language (default: python)
        timeout: Timeout in seconds (default: 30)
        memory_limit: Memory limit (e.g., 128Mi, 512Mi, 1Gi) (default: None - uses dispatcher default)
        cpu_limit: CPU limit (e.g., 100m, 500m, 1) (default: None - uses dispatcher default)
        executor_image: Executor image name (e.g., 'executor-base') or full image path (default: None)
        debug: Preserve pod for debugging if it fails (default: False)
        priority: Priority level: 1=high, 0=normal, -1=low (default: -1 for test evaluations)
        
    Returns:
        Evaluation ID
    """
    payload = {
        "code": code,
        "language": language,
        "timeout": timeout,
        "debug": debug,
        "priority": priority  # Always include priority (default -1 for tests)
    }
    
    # Add optional parameters if provided
    if memory_limit is not None:
        payload["memory_limit"] = memory_limit
    if cpu_limit is not None:
        payload["cpu_limit"] = cpu_limit
    if executor_image:
        payload["executor_image"] = executor_image
    
    response = requests.post(
        f"{API_URL}/eval",
        json=payload
    )
    response.raise_for_status()
    data = response.json()
    eval_id = data.get("eval_id")
    print(f"\n[EVAL_SUBMIT] eval_id={eval_id} timestamp={time.time()}")
    return eval_id


def get_evaluation_status(eval_id: str) -> Dict[str, Any]:
    """Get the status of an evaluation
    
    Args:
        eval_id: Evaluation ID
        
    Returns:
        Evaluation status and results
    """
    response = requests.get(f"{API_URL}/eval/{eval_id}")
    response.raise_for_status()
    return response.json()


def wait_for_completion(eval_id: str, timeout: int = 60, use_adaptive: bool = False) -> Dict[str, Any]:
    """Wait for an evaluation to complete
    
    Args:
        eval_id: Evaluation ID
        timeout: Maximum time to wait in seconds
        use_adaptive: Use adaptive waiting with resource checking (for tests under load)
        
    Returns:
        Final evaluation result
        
    Raises:
        TimeoutError: If evaluation doesn't complete within timeout
    """
    if use_adaptive:
        from .adaptive_timeouts import AdaptiveWaiter
        waiter = AdaptiveWaiter(initial_timeout=timeout)
        
        with requests.Session() as session:
            results = waiter.wait_for_evaluations(
                api_session=session,
                api_base_url=API_URL,
                eval_ids=[eval_id],
                check_resources=True
            )
        
        if eval_id not in results['completed'] and eval_id not in results['failed']:
            raise TimeoutError(f"Evaluation {eval_id} did not complete within {timeout} seconds")
        
        return get_evaluation_status(eval_id)
    
    # Simple waiting logic
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        result = get_evaluation_status(eval_id)
        status = result.get("status", "unknown")
        
        if status in ["completed", "failed", "timeout", "cancelled"]:
            return result
            
        time.sleep(0.5)
    
    raise TimeoutError(f"Evaluation {eval_id} did not complete within {timeout} seconds")


def wait_for_logs(eval_id: str, timeout: int = 30) -> str:
    """Wait for evaluation logs to be available
    
    This handles the race condition where logs might not be immediately available
    when an evaluation completes. The storage worker fetches logs asynchronously
    after storing the completion status.
    
    Args:
        eval_id: Evaluation ID
        timeout: Maximum time to wait for logs in seconds
        
    Returns:
        The evaluation output/logs
        
    Raises:
        TimeoutError: If logs don't appear within timeout
    """
    start_time = time.time()
    last_output = ""
    
    while time.time() - start_time < timeout:
        result = get_evaluation_status(eval_id)
        output = result.get("output", "")
        
        # If we have non-empty output, return it
        if output and output.strip():
            return output
            
        # Check if evaluation failed with error message
        if result.get("status") in ["failed", "timeout", "cancelled"]:
            error = result.get("error", "")
            if error:
                return error
                
        last_output = output
        time.sleep(0.5)
    
    # Timeout waiting for logs
    raise TimeoutError(
        f"Logs for evaluation {eval_id} did not appear within {timeout} seconds. "
        f"Last output: {repr(last_output)}"
    )