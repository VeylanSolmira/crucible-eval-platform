"""
Adaptive timeout utilities for tests running in resource-constrained environments.

Provides better feedback and dynamic timeout adjustment based on progress.
"""

import time
import subprocess
import json
import pytest
from typing import List, Dict, Optional, Callable


class AdaptiveWaiter:
    """Provides adaptive waiting with progress feedback."""
    
    def __init__(self, initial_timeout: float = 60.0):
        self.initial_timeout = initial_timeout
        self.start_time = time.time()
        self.last_progress_time = time.time()
        self.completed_count = 0
        self.last_status_check = 0
        
    def wait_for_evaluations(self, 
                           api_session,
                           api_base_url: str,
                           eval_ids: List[str],
                           check_resources: bool = True) -> Dict[str, any]:
        """
        Wait for evaluations with adaptive timeout and progress feedback.
        
        Returns dict with results and statistics.
        """
        total_count = len(eval_ids)
        completed = set()
        failed = set()
        
        # Calculate initial timeout based on resource availability
        timeout = self._calculate_timeout(total_count, check_resources)
        
        print(f"\n=== Adaptive Evaluation Wait ===")
        print(f"Total evaluations: {total_count}")
        print(f"Timeout: {timeout}s")
        
        if check_resources:
            self._print_resource_status()
        
        while len(completed) + len(failed) < total_count:
            current_time = time.time()
            elapsed = current_time - self.start_time
            
            # Check if timeout exceeded
            if elapsed > timeout:
                remaining = total_count - len(completed) - len(failed)
                print(f"\n❌ Timeout after {elapsed:.1f}s with {remaining} evaluations incomplete")
                break
                
            # Check progress periodically
            if current_time - self.last_status_check > 2.0:
                self.last_status_check = current_time
                new_completed, new_failed = self._check_evaluations(
                    api_session, api_base_url, eval_ids, completed, failed
                )
                
                # Update progress
                if new_completed or new_failed:
                    self.last_progress_time = current_time
                    completed.update(new_completed)
                    failed.update(new_failed)
                    
                    print(f"\n[{elapsed:.1f}s] Progress: "
                          f"{len(completed)} completed, "
                          f"{len(failed)} failed, "
                          f"{total_count - len(completed) - len(failed)} pending")
                    
                    # Extend timeout if making progress
                    if elapsed > timeout * 0.8:
                        timeout = min(timeout * 1.2, 300)  # Max 5 minutes
                        print(f"  → Extended timeout to {timeout}s due to progress")
                        
                # No progress warning
                elif current_time - self.last_progress_time > 30:
                    print(f"\n⚠️  No progress in {current_time - self.last_progress_time:.0f}s")
                    if check_resources:
                        self._print_resource_status()
                        
            time.sleep(0.5)
            
        # Final summary
        duration = time.time() - self.start_time
        print(f"\n=== Evaluation Summary ===")
        print(f"Duration: {duration:.1f}s")
        print(f"Completed: {len(completed)}")
        print(f"Failed: {len(failed)}")
        print(f"Incomplete: {total_count - len(completed) - len(failed)}")
        
        return {
            "completed": list(completed),
            "failed": list(failed),
            "duration": duration,
            "timeout_used": timeout
        }
        
    def _calculate_timeout(self, count: int, check_resources: bool) -> float:
        """Calculate timeout based on evaluation count and resources."""
        base_timeout = self.initial_timeout
        
        if not check_resources:
            return base_timeout
            
        # Check available memory for concurrent execution
        try:
            result = subprocess.run(
                ["kubectl", "get", "resourcequota", "evaluation-quota", 
                 "-n", "crucible", "-o", "json"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                quota = json.loads(result.stdout)
                memory_limit = quota['status']['hard']['limits.memory']
                memory_used = quota['status']['used']['limits.memory']
                
                # Parse memory values (e.g., "6Gi" -> 6144, "3116Mi" -> 3116)
                limit_mb = self._parse_memory(memory_limit)
                used_mb = self._parse_memory(memory_used)
                available_mb = limit_mb - used_mb
                
                # Each evaluation needs ~512Mi
                max_concurrent = max(1, available_mb // 512)
                
                # Calculate waves needed
                waves = (count + max_concurrent - 1) // max_concurrent
                
                # 10s per wave + overhead
                calculated_timeout = waves * 10 + 20
                
                print(f"Resource-based timeout: {calculated_timeout}s "
                      f"({waves} waves with {max_concurrent} concurrent)")
                
                return max(base_timeout, calculated_timeout)
                
        except Exception as e:
            print(f"Could not calculate resource-based timeout: {e}")
            
        return base_timeout
        
    def _parse_memory(self, memory_str: str) -> int:
        """Parse memory string to MB."""
        if memory_str.endswith('Gi'):
            return int(memory_str[:-2]) * 1024
        elif memory_str.endswith('Mi'):
            return int(memory_str[:-2])
        else:
            return 0
            
    def _check_evaluations(self, api_session, api_base_url: str, 
                          eval_ids: List[str], 
                          completed: set, failed: set) -> tuple:
        """Check evaluation statuses and return newly completed/failed."""
        new_completed = set()
        new_failed = set()
        
        for eval_id in eval_ids:
            if eval_id in completed or eval_id in failed:
                continue
                
            try:
                response = api_session.get(f"{api_base_url}/eval/{eval_id}")
                if response.status_code == 200:
                    status = response.json()["status"]
                    if status == "completed":
                        new_completed.add(eval_id)
                    elif status in ["failed", "timeout"]:
                        new_failed.add(eval_id)
            except Exception:
                pass  # Ignore errors in status checks
                
        return new_completed, new_failed
        
    def _print_resource_status(self):
        """Print current resource usage."""
        try:
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", "crucible", 
                 "-l", "app=evaluation", "--no-headers"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                pods = result.stdout.strip().split('\n') if result.stdout.strip() else []
                running = sum(1 for pod in pods if 'Running' in pod)
                pending = sum(1 for pod in pods if 'Pending' in pod)
                
                print(f"  Resource status: {running} running, {pending} pending evaluation pods")
                
        except Exception:
            pass


def wait_with_progress(api_session, api_base_url: str, eval_ids: List[str], 
                      timeout: float = 60.0, check_resources: bool = True) -> Dict:
    """
    Convenience function for waiting with adaptive timeout and progress.
    
    Usage:
        results = wait_with_progress(api_session, api_base_url, eval_ids)
        if len(results["completed"]) < len(eval_ids):
            pytest.fail(f"Only {len(results['completed'])} of {len(eval_ids)} completed")
    """
    waiter = AdaptiveWaiter(timeout)
    return waiter.wait_for_evaluations(api_session, api_base_url, eval_ids, check_resources)