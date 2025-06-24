"""
Remote Queue Client - Adapts TaskQueue interface to remote HTTP service
This allows gradual migration from in-process to networked queue
"""
import os
import httpx  # Already included in base image with FastAPI
from typing import Dict, Any, Callable
from datetime import datetime

class RemoteTaskQueue:
    """
    Drop-in replacement for TaskQueue that uses remote HTTP service.
    
    This adapter pattern allows us to switch between local and remote
    queue implementations without changing the platform code.
    """
    
    def __init__(self, queue_url: str = None, api_key: str = None):
        self.queue_url = queue_url or os.getenv("QUEUE_SERVICE_URL", "http://localhost:8081")
        self.api_key = api_key or os.getenv("QUEUE_API_KEY")
        
        # Create HTTP client
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        self.client = httpx.Client(base_url=self.queue_url, headers=headers, timeout=30.0)
        
        # Track submitted tasks (in real implementation, this would be in Redis)
        self.submitted_tasks = {}
    
    def submit(self, eval_id: str, func: Callable, *args, **kwargs) -> None:
        """Submit a task to the remote queue"""
        # For remote queue, we can't send the function itself
        # We need to extract the code from the kwargs
        code = kwargs.get('code', '')
        engine = kwargs.get('engine', 'docker')
        
        # Send to remote queue
        response = self.client.post("/tasks", json={
            "eval_id": eval_id,
            "code": code,
            "engine": engine,
            "priority": 1
        })
        response.raise_for_status()
        
        # Track submission
        self.submitted_tasks[eval_id] = {
            'status': 'queued',
            'submitted_at': datetime.utcnow()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get queue status from remote service"""
        response = self.client.get("/status")
        response.raise_for_status()
        return response.json()
    
    def wait_for_task(self, eval_id: str, timeout: float = 30) -> str:
        """Wait for a specific task to complete"""
        # This would poll the remote service
        # For now, return a simple status
        return self.submitted_tasks.get(eval_id, {}).get('status', 'unknown')
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for the remote queue"""
        try:
            response = self.client.get("/health")
            response.raise_for_status()
            data = response.json()
            return {
                'healthy': data.get('status') == 'healthy',
                'component': 'RemoteTaskQueue',
                'remote_url': self.queue_url,
                **data
            }
        except Exception as e:
            return {
                'healthy': False,
                'component': 'RemoteTaskQueue',
                'error': str(e)
            }
    
    def shutdown(self, wait: bool = True) -> None:
        """Close the HTTP client"""
        self.client.close()
    
    def self_test(self) -> Dict[str, Any]:
        """Test remote queue connectivity"""
        tests_passed = []
        tests_failed = []
        
        # Test 1: Can reach queue service
        try:
            health = self.health_check()
            if health['healthy']:
                tests_passed.append("Remote queue connectivity")
            else:
                tests_failed.append(f"Remote queue unhealthy: {health.get('error', 'Unknown')}")
        except Exception as e:
            tests_failed.append(f"Remote queue connection failed: {str(e)}")
        
        # Test 2: Can get status
        try:
            status = self.get_status()
            if isinstance(status, dict) and 'queued' in status:
                tests_passed.append("Status endpoint working")
            else:
                tests_failed.append("Invalid status response")
        except Exception as e:
            tests_failed.append(f"Status check failed: {str(e)}")
        
        return {
            'passed': len(tests_failed) == 0,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'message': f"Passed {len(tests_passed)}/{len(tests_passed) + len(tests_failed)} tests"
        }