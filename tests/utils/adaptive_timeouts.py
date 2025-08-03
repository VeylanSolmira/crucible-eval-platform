"""
Adaptive timeout utilities for tests running in resource-constrained environments.

Provides better feedback and dynamic timeout adjustment based on progress.
"""

import time
import subprocess
import json
import pytest
import os
from typing import List, Dict, Optional, Callable
from shared.constants.evaluation_defaults import DEFAULT_MEMORY_MB


class AdaptiveWaiter:
    """Provides adaptive waiting with progress feedback."""
    
    def __init__(self, initial_timeout: float = 60.0):
        self.initial_timeout = initial_timeout
        self.start_time = time.time()
        self.last_progress_time = time.time()
        self.completed_count = 0
        self.last_status_check = 0
        self.verbose = os.environ.get('VERBOSE_TESTS', 'false').lower() == 'true'
        # Get namespace from environment - REQUIRED for tests
        self.namespace = os.environ.get('K8S_NAMESPACE')
        if not self.namespace:
            raise ValueError("K8S_NAMESPACE environment variable must be set for adaptive timeout checks")
        
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
                
                # Print diagnostic info for incomplete evaluations
                for eval_id in eval_ids:
                    if eval_id not in completed and eval_id not in failed:
                        try:
                            response = api_session.get(f"{api_base_url}/eval/{eval_id}")
                            if response.status_code == 200:
                                data = response.json()
                                status = data.get("status", "unknown")
                                print(f"\n⏱️  Timed out evaluation: {eval_id}")
                                print(f"   Last status: {status}")
                                print(f"   Check status: curl http://api-service:8080/api/eval/{eval_id}")
                        except Exception:
                            pass
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
                        
                        # Check if cluster is at capacity
                        if self._is_cluster_at_capacity():
                            # Cluster is busy, this is expected - extend timeout
                            print("  → Cluster at capacity - extending timeout")
                            timeout = min(timeout * 1.2, 600)  # Max 10 minutes
                            # Reset the "no progress" timer since this is expected
                            self.last_progress_time = current_time
                            
                            # Print detailed resource information if verbose
                            if self.verbose:
                                # Pass only the eval IDs we're still waiting for
                                pending_eval_ids = [eid for eid in eval_ids if eid not in completed and eid not in failed]
                                self._print_detailed_resource_status(pending_eval_ids)
                        
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
                 "-n", self.namespace, "-o", "json"],
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
                
                # Each evaluation needs DEFAULT_MEMORY_MB
                max_concurrent = max(1, available_mb // DEFAULT_MEMORY_MB)
                
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
                    data = response.json()
                    status = data.get("status", "unknown")
                    # Always print detailed status for each pending evaluation
                    elapsed = time.time() - self.start_time
                    print(f"  [{elapsed:.1f}s] {eval_id}: {status}")
                    
                    if status == "completed":
                        new_completed.add(eval_id)
                    elif status in ["failed", "timeout"]:
                        new_failed.add(eval_id)
            except Exception as e:
                print(f"  Error checking {eval_id}: {e}")  # Show errors instead of hiding them
                
        return new_completed, new_failed
        
    def _print_resource_status(self):
        """Print current resource usage."""
        try:
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", self.namespace, 
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
    
    def _is_cluster_at_capacity(self) -> bool:
        """Check if cluster is at or near resource capacity."""
        try:
            is_memory_constrained = False
            has_running_evaluations = False
            
            # Check ResourceQuota
            result = subprocess.run(
                ["kubectl", "get", "resourcequota", "evaluation-quota", 
                 "-n", self.namespace, "-o", "json"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                quota = json.loads(result.stdout)
                memory_limit = quota['status']['hard'].get('limits.memory', '0')
                memory_used = quota['status']['used'].get('limits.memory', '0')
                
                # Parse memory values
                limit_mb = self._parse_memory(memory_limit)
                used_mb = self._parse_memory(memory_used)
                available_mb = limit_mb - used_mb
                
                if self.verbose:
                    print(f"    Quota check: {used_mb}MB used / {limit_mb}MB limit ({available_mb}MB available)")
                
                # Check if less than one evaluation's worth of memory is available
                if available_mb < DEFAULT_MEMORY_MB:
                    is_memory_constrained = True
            else:
                if self.verbose:
                    print(f"    Failed to get ResourceQuota: {result.stderr}")
                    
            # Check if there are RUNNING or PENDING evaluation pods
            # First check running pods
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", self.namespace, 
                 "-l", "app=evaluation", "--field-selector=status.phase=Running", "--no-headers"],
                capture_output=True, text=True
            )
            
            running_count = 0
            if result.returncode == 0 and result.stdout.strip():
                has_running_evaluations = True
                running_count = len(result.stdout.strip().split('\n'))
                
            # Also check pending pods
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", self.namespace, 
                 "-l", "app=evaluation", "--field-selector=status.phase=Pending", "--no-headers"],
                capture_output=True, text=True
            )
            
            pending_count = 0
            if result.returncode == 0 and result.stdout.strip():
                pending_count = len(result.stdout.strip().split('\n'))
                
            if self.verbose:
                print(f"    Evaluation pods: {running_count} running, {pending_count} pending")
            
            # Consider at capacity if:
            # 1. Memory is constrained AND
            # 2. There are running OR pending evaluations that might eventually free up resources
            # If we have pending pods with no memory, they're waiting for resources
            at_capacity = is_memory_constrained and (has_running_evaluations or pending_count > 0)
            
            if self.verbose:
                if is_memory_constrained and pending_count > 0 and not has_running_evaluations:
                    print("    Memory constrained with only pending pods - severe contention!")
                elif at_capacity:
                    print("    Cluster at capacity - will extend timeout")
                
            return at_capacity
                
        except Exception as e:
            if self.verbose:
                print(f"    Error checking capacity: {e}")
            
        return False
    
    def _print_detailed_resource_status(self, waiting_eval_ids: List[str]):
        """Print detailed resource information when verbose mode is enabled."""
        print("\n  === Detailed Resource Status ===")
        
        # Get ResourceQuota details
        try:
            result = subprocess.run(
                ["kubectl", "get", "resourcequota", "evaluation-quota", 
                 "-n", self.namespace, "-o", "json"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                quota = json.loads(result.stdout)
                memory_limit = quota['status']['hard'].get('limits.memory', '0')
                memory_used = quota['status']['used'].get('limits.memory', '0')
                cpu_limit = quota['status']['hard'].get('limits.cpu', '0')
                cpu_used = quota['status']['used'].get('limits.cpu', '0')
                
                print(f"  ResourceQuota:")
                print(f"    Memory: {memory_used} / {memory_limit}")
                print(f"    CPU: {cpu_used} / {cpu_limit}")
        except Exception as e:
            print(f"  Could not get ResourceQuota: {e}")
        
        # Get all evaluation pods with their status
        try:
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", self.namespace, 
                 "-l", "app=evaluation", "-o", "json"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                pods_data = json.loads(result.stdout)
                pods = pods_data.get('items', [])
                
                running_pods = []
                pending_pods = []
                failed_pods = []
                
                for pod in pods:
                    pod_name = pod['metadata']['name']
                    phase = pod['status']['phase']
                    
                    # Extract eval ID from pod name (format: evaluation-<eval_id>-job-<suffix>)
                    eval_id = None
                    if pod_name.startswith('evaluation-') and '-job-' in pod_name:
                        eval_id = pod_name.split('-job-')[0].replace('evaluation-', '')
                    
                    if phase == 'Running':
                        running_pods.append((pod_name, eval_id))
                    elif phase == 'Pending':
                        pending_pods.append((pod_name, eval_id))
                    elif phase == 'Failed':
                        failed_pods.append((pod_name, eval_id))
                
                print(f"\n  Evaluation Pods:")
                if running_pods:
                    print(f"    Running ({len(running_pods)}):")
                    for pod_name, eval_id in running_pods[:5]:  # Show first 5
                        in_waiting = eval_id in waiting_eval_ids if eval_id else False
                        waiting_marker = " [WAITING]" if in_waiting else ""
                        print(f"      - {pod_name}{waiting_marker}")
                    if len(running_pods) > 5:
                        print(f"      ... and {len(running_pods) - 5} more")
                
                if pending_pods:
                    print(f"    Pending ({len(pending_pods)}):")
                    for pod_name, eval_id in pending_pods[:5]:
                        in_waiting = eval_id in waiting_eval_ids if eval_id else False
                        waiting_marker = " [WAITING]" if in_waiting else ""
                        print(f"      - {pod_name}{waiting_marker}")
                    if len(pending_pods) > 5:
                        print(f"      ... and {len(pending_pods) - 5} more")
                
                if failed_pods:
                    print(f"    Failed ({len(failed_pods)}):")
                    for pod_name, eval_id in failed_pods[:3]:
                        print(f"      - {pod_name}")
                    if len(failed_pods) > 3:
                        print(f"      ... and {len(failed_pods) - 3} more")
                
                # Show which eval IDs we're waiting for that don't have pods
                eval_ids_with_pods = set()
                for _, eval_id in running_pods + pending_pods + failed_pods:
                    if eval_id:
                        eval_ids_with_pods.add(eval_id)
                
                missing_eval_ids = set(waiting_eval_ids) - eval_ids_with_pods
                if missing_eval_ids:
                    print(f"\n  Evaluations without pods ({len(missing_eval_ids)}):")
                    for eval_id in list(missing_eval_ids)[:5]:
                        print(f"    - {eval_id}")
                    if len(missing_eval_ids) > 5:
                        print(f"    ... and {len(missing_eval_ids) - 5} more")
                        
        except Exception as e:
            print(f"  Could not get pod details: {e}")
        
        print("  === End Detailed Status ===")


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