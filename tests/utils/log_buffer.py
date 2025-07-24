"""
Simple log buffer for test results.

Captures and stores test logs before pod deletion to ensure we don't lose
important debugging information when the cleanup controller removes pods.
"""

import redis
import json
import os
from datetime import datetime
from typing import Optional, List, Dict
import subprocess


class TestLogBuffer:
    """Lightweight log buffer for test results."""
    
    def __init__(self, redis_url: Optional[str] = None, max_logs: int = 100):
        # Redis URL must be provided explicitly or via environment
        if not redis_url:
            redis_url = os.environ.get("REDIS_URL")
            if not redis_url:
                raise ValueError(
                    "REDIS_URL environment variable must be set. "
                    "Example: REDIS_URL=redis://redis.crucible.svc.cluster.local:6379/0"
                )
            
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.max_logs = max_logs
        self.log_key_prefix = "test_logs"
        
    def capture_pod_logs(self, pod_name: str, namespace: Optional[str] = None) -> Optional[str]:
        """Capture logs from a pod before it's deleted."""
        if not namespace:
            namespace = os.environ.get("K8S_NAMESPACE")
            if not namespace:
                raise ValueError(
                    "K8S_NAMESPACE environment variable must be set when namespace not provided. "
                    "Example: K8S_NAMESPACE=crucible"
                )
            
        try:
            # Use kubectl to get logs
            result = subprocess.run(
                ["kubectl", "logs", pod_name, "-n", namespace, "--tail=1000"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error capturing logs: {result.stderr}"
                
        except Exception as e:
            return f"Exception capturing logs: {str(e)}"
    
    def store_test_result(self, test_id: str, suite: str, status: str, logs: str, 
                         metadata: Optional[Dict] = None):
        """Store test result with logs."""
        timestamp = datetime.utcnow().isoformat()
        
        result = {
            "test_id": test_id,
            "suite": suite,
            "status": status,
            "timestamp": timestamp,
            "logs": logs[-10000:],  # Keep last 10k chars to prevent huge entries
            "metadata": metadata or {}
        }
        
        # Store in Redis list
        key = f"{self.log_key_prefix}:results"
        self.redis_client.lpush(key, json.dumps(result))
        self.redis_client.ltrim(key, 0, self.max_logs - 1)  # Keep only recent results
        
        # Also store by test_id for quick lookup
        self.redis_client.setex(
            f"{self.log_key_prefix}:{test_id}", 
            3600,  # Expire after 1 hour
            json.dumps(result)
        )
        
    def get_recent_results(self, count: int = 10) -> List[Dict]:
        """Get recent test results."""
        key = f"{self.log_key_prefix}:results"
        results = self.redis_client.lrange(key, 0, count - 1)
        return [json.loads(r) for r in results]
    
    def get_test_logs(self, test_id: str) -> Optional[Dict]:
        """Get logs for a specific test."""
        result = self.redis_client.get(f"{self.log_key_prefix}:{test_id}")
        return json.loads(result) if result else None
    
    def cleanup_old_logs(self, keep_hours: int = 24):
        """Clean up logs older than specified hours."""
        # This would need to iterate through the list and remove old entries
        # For now, we rely on Redis key expiration and list trimming
        pass