"""Common utilities for integration tests"""

import time
import requests
import os
from typing import Dict, Any, Optional


# Get API URL from environment or use default
API_URL = os.getenv("API_BASE_URL", os.getenv("API_URL", "http://localhost:8080/api"))


def submit_evaluation(code: str, language: str = "python", timeout: int = 30) -> str:
    """Submit an evaluation to the API
    
    Args:
        code: Code to evaluate
        language: Programming language (default: python)
        timeout: Timeout in seconds (default: 30)
        
    Returns:
        Evaluation ID
    """
    response = requests.post(
        f"{API_URL}/eval",
        json={
            "code": code,
            "language": language,
            "timeout": timeout
        }
    )
    response.raise_for_status()
    data = response.json()
    return data.get("eval_id")


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


def wait_for_completion(eval_id: str, timeout: int = 60) -> Dict[str, Any]:
    """Wait for an evaluation to complete
    
    Args:
        eval_id: Evaluation ID
        timeout: Maximum time to wait in seconds
        
    Returns:
        Final evaluation result
        
    Raises:
        TimeoutError: If evaluation doesn't complete within timeout
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        result = get_evaluation_status(eval_id)
        status = result.get("status", "unknown")
        
        if status in ["completed", "failed", "timeout", "cancelled"]:
            return result
            
        time.sleep(0.5)
    
    raise TimeoutError(f"Evaluation {eval_id} did not complete within {timeout} seconds")