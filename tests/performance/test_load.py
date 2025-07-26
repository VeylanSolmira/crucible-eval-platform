#!/usr/bin/env python3
"""
Load testing for the platform with rate limit awareness.

This test respects nginx rate limits while still creating significant load.
Rate limits: API endpoints allow 10 req/s with burst of 10.

Features:
- Token bucket rate limiting to avoid 429 errors
- Support for both HTTP polling and Redis pub/sub monitoring
- State machine integration for handling out-of-order events
- Detailed performance metrics collection
"""

import json
import os
import time
import requests
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict, Optional
import threading
from collections import deque
from datetime import datetime, timedelta
import redis
import asyncio
import pytest

API_BASE_URL = os.environ.get("API_BASE_URL", "http://api-service:8080/api")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
STORAGE_SERVICE_URL = os.environ.get("STORAGE_SERVICE_URL", "http://storage-service:8082")

# Terminal states for evaluations
TERMINAL_STATES = ["completed", "failed", "cancelled", "timeout"]

# Rate limiting configuration
MAX_REQUESTS_PER_SECOND = 10  # nginx limit
BURST_ALLOWANCE = 10  # nginx burst
RATE_LIMIT_WINDOW = 1.0  # 1 second

# Monitoring mode
MONITOR_MODE = os.environ.get("MONITOR_MODE", "batch")  # "http", "batch", or "redis"


class RateLimiter:
    """Token bucket rate limiter to prevent 429 errors."""
    
    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.time()
        self.lock = threading.Lock()
    
    def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens, blocking if necessary.
        Returns the wait time (0 if no wait was needed).
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.last_update = now
            
            # Add tokens based on elapsed time
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            
            # Wait if not enough tokens
            wait_time = 0
            if self.tokens < tokens:
                wait_time = (tokens - self.tokens) / self.rate
                time.sleep(wait_time)
                self.tokens = tokens
                self.last_update = time.time()
            
            self.tokens -= tokens
            return wait_time


class LoadTestResult:
    """Track results from a single evaluation submission."""
    
    def __init__(self):
        self.eval_id: str = ""
        self.submit_time: float = 0.0
        self.complete_time: float = 0.0
        self.total_duration: float = 0.0
        self.queue_time: float = 0.0
        self.execution_time: float = 0.0
        self.status: str = ""
        self.error: str = ""
        self.rate_limited: bool = False
        self.wait_time: float = 0.0
        self.submit_timestamp: float = 0.0  # When evaluation was submitted
        self.code_type: str = ""  # Type of code (Fast/Medium/Slow)


# Global rate limiter
rate_limiter = RateLimiter(MAX_REQUESTS_PER_SECOND, BURST_ALLOWANCE)


def submit_evaluation(index: int, code: str) -> Tuple[Optional[str], LoadTestResult]:
    """Submit an evaluation and return eval_id and initial result."""
    result = LoadTestResult()
    
    try:
        # Wait for rate limit token
        wait_time = rate_limiter.acquire()
        result.wait_time = wait_time
        
        # Submit evaluation
        start_time = time.time()
        eval_request = {
            "code": code,
            "language": "python",
            "engine": "docker",
            "timeout": 60
        }
        
        response = requests.post(f"{API_BASE_URL}/eval", json=eval_request, timeout=10)
        
        if response.status_code == 429:
            result.rate_limited = True
            result.error = "Rate limited despite token bucket"
            result.status = "rate_limited"
            return None, result
            
        response.raise_for_status()
        result.eval_id = response.json()["eval_id"]
        result.submit_time = time.time() - start_time
        result.status = "submitted"
        
        # Store submission timestamp for later monitoring
        result.submit_timestamp = time.time()
        
        return result.eval_id, result
        
    except Exception as e:
        result.error = str(e)
        result.status = "submit_error"
        result.submit_time = time.time() - start_time
        return None, result


def monitor_evaluation_http(eval_id: str, result: LoadTestResult, timeout: int = 120) -> LoadTestResult:
    """Monitor a single evaluation via HTTP polling with exponential backoff."""
    start_time = result.submit_timestamp
    queue_start = time.time()
    execution_start = None
    
    # Exponential backoff parameters
    min_interval = 0.5
    max_interval = 10.0
    backoff_factor = 1.5
    poll_interval = min_interval
    consecutive_failures = 0
    
    end_time = time.time() + timeout
    
    while time.time() < end_time:
        # Rate limit status checks with exponential backoff
        rate_limiter.acquire(0.1)  # Use fractional tokens for status checks
        
        try:
            # Increase timeout based on load
            request_timeout = min(30, 5 + consecutive_failures * 2)
            response = requests.get(f"{API_BASE_URL}/eval/{eval_id}", timeout=request_timeout)
            
            if response.status_code == 200:
                status_data = response.json()
                result.status = status_data.get("status", "unknown")
                
                # Track when execution starts
                if result.status == "running" and execution_start is None:
                    execution_start = time.time()
                    result.queue_time = execution_start - queue_start
                
                if result.status in TERMINAL_STATES:
                    current_time = time.time()
                    result.complete_time = current_time - start_time
                    result.total_duration = result.complete_time
                    
                    if execution_start:
                        result.execution_time = current_time - execution_start
                    break
                
                # Reset backoff on success
                consecutive_failures = 0
                poll_interval = min_interval
                
            elif response.status_code == 429:
                # Rate limited - back off more aggressively
                consecutive_failures += 1
                poll_interval = min(max_interval, poll_interval * backoff_factor * 2)
            else:
                consecutive_failures += 1
                
        except Exception as e:
            # Exponential backoff on failures
            consecutive_failures += 1
            poll_interval = min(max_interval, poll_interval * backoff_factor)
            
        time.sleep(poll_interval)
    
    if result.status not in TERMINAL_STATES:
        result.error = "Timeout waiting for completion"
        result.status = "timeout"
        result.total_duration = time.time() - start_time
    
    return result


def monitor_evaluations_batch(eval_ids: List[str], results_dict: Dict[str, LoadTestResult], timeout: int = 300) -> None:
    """
    Monitor multiple evaluations using batch status checks to reduce load.
    Updates LoadTestResult objects in-place.
    """
    print(f"\n📊 Monitoring {len(eval_ids)} evaluations using batch status checks...")
    
    start_time = time.time()
    end_time = start_time + timeout
    
    # Track which evaluations are complete
    incomplete = set(eval_ids)
    
    # Adaptive monitoring parameters
    min_interval = 1.0
    max_interval = 30.0
    poll_interval = min_interval
    consecutive_failures = 0
    backoff_factor = 1.5
    
    # Progress tracking
    last_progress = start_time
    completed_count = 0
    
    while incomplete and time.time() < end_time:
        # Rate limit batch checks
        rate_limiter.acquire(0.5)  # Use more tokens for batch requests
        
        try:
            # Check status of all incomplete evaluations
            # Note: This assumes the API supports batch status checks
            # If not, we'll fall back to individual checks with larger intervals
            batch_statuses = {}
            
            # Try to get all statuses (this is more efficient than individual requests)
            # First check if there's a batch endpoint
            batch_size = min(50, len(incomplete))  # Limit batch size
            
            for batch_start in range(0, len(incomplete), batch_size):
                batch_eval_ids = list(incomplete)[batch_start:batch_start + batch_size]
                
                # Check each evaluation in the batch
                for eval_id in batch_eval_ids:
                    try:
                        response = requests.get(
                            f"{API_BASE_URL}/eval/{eval_id}", 
                            timeout=min(30, 10 + consecutive_failures * 2)
                        )
                        if response.status_code == 200:
                            batch_statuses[eval_id] = response.json()
                    except:
                        pass  # Will retry in next iteration
                
                # Small delay between batches to avoid overwhelming the API
                if batch_start + batch_size < len(incomplete):
                    time.sleep(0.1)
            
            # Process results
            newly_completed = []
            for eval_id, status_data in batch_statuses.items():
                result = results_dict[eval_id]
                old_status = result.status
                result.status = status_data.get("status", "unknown")
                
                # Track state transitions
                current_time = time.time()
                if result.status == "running" and old_status != "running":
                    result.queue_time = current_time - result.submit_timestamp
                
                if result.status in TERMINAL_STATES:
                    result.total_duration = current_time - result.submit_timestamp
                    result.complete_time = result.total_duration
                    
                    if result.queue_time > 0:
                        result.execution_time = result.total_duration - result.queue_time
                    
                    incomplete.remove(eval_id)
                    newly_completed.append(eval_id)
                    completed_count += 1
            
            # Reset backoff on successful batch
            if batch_statuses:
                consecutive_failures = 0
                poll_interval = min_interval
            else:
                consecutive_failures += 1
                poll_interval = min(max_interval, poll_interval * backoff_factor)
            
            # Progress update
            current_time = time.time()
            if current_time - last_progress > 5 or newly_completed:
                elapsed = current_time - start_time
                rate = completed_count / elapsed if elapsed > 0 else 0
                print(f"  Progress: {completed_count}/{len(eval_ids)} completed "
                      f"({len(incomplete)} remaining) - Rate: {rate:.1f}/s")
                last_progress = current_time
                
        except Exception as e:
            print(f"  Batch monitoring error: {e}")
            consecutive_failures += 1
            poll_interval = min(max_interval, poll_interval * backoff_factor)
        
        # Adaptive sleep based on cluster load
        if incomplete:
            # Increase interval based on number of pending evaluations
            load_factor = min(2.0, len(incomplete) / 50.0)
            adjusted_interval = poll_interval * (1 + load_factor)
            time.sleep(min(adjusted_interval, max_interval))
    
    # Mark any remaining as timeout
    for eval_id in incomplete:
        result = results_dict[eval_id]
        if result.status not in TERMINAL_STATES:
            result.status = "timeout"
            result.error = "Batch monitoring timeout"
            result.total_duration = time.time() - result.submit_timestamp
    
    final_time = time.time() - start_time
    print(f"\n✅ Batch monitoring complete in {final_time:.1f}s")
    print(f"   Completed: {completed_count}/{len(eval_ids)}")


def monitor_evaluations_redis(results_dict: Dict[str, LoadTestResult], timeout: int = 300) -> None:
    """
    Monitor evaluations via Redis pub/sub (grey-box approach).
    Updates LoadTestResult objects in-place.
    """
    eval_ids = list(results_dict.keys())
    print(f"\n📡 Monitoring {len(eval_ids)} evaluations via Redis pub/sub...")
    
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    
    # Subscribe to evaluation events
    pubsub.subscribe(
        "evaluation:queued",
        "evaluation:running",
        "evaluation:completed", 
        "evaluation:failed"
    )
    
    completed = set()
    start_time = time.time()
    last_progress = start_time
    
    # Track state transitions for timing calculations
    state_times = {eval_id: {} for eval_id in eval_ids}
    
    try:
        while len(completed) < len(eval_ids) and time.time() - start_time < timeout:
            message = pubsub.get_message(timeout=1.0)
            if message and message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    eval_id = data.get("eval_id")
                    
                    if eval_id in eval_ids and eval_id in results_dict:
                        channel = message["channel"]
                        status = channel.split(":")[-1]
                        current_time = time.time()
                        
                        # Update state tracking
                        state_times[eval_id][status] = current_time
                        result = results_dict[eval_id]
                        
                        # Update status
                        result.status = status
                        
                        # Calculate timings
                        if status == "queued" and "queued" not in state_times[eval_id]:
                            # First time seeing queued status
                            pass
                        elif status == "running":
                            # Calculate queue time
                            if result.submit_timestamp:
                                result.queue_time = current_time - result.submit_timestamp
                        elif status in [s for s in TERMINAL_STATES if s != "cancelled"]:
                            # Calculate total duration
                            if result.submit_timestamp:
                                result.total_duration = current_time - result.submit_timestamp
                                result.complete_time = result.total_duration
                                
                                # Calculate execution time
                                if "running" in state_times[eval_id]:
                                    result.execution_time = current_time - state_times[eval_id]["running"]
                                elif result.queue_time:
                                    result.execution_time = result.total_duration - result.queue_time
                            
                            completed.add(eval_id)
                            
                        # Progress updates
                        if current_time - last_progress > 5:
                            print(f"  Progress: {len(completed)}/{len(eval_ids)} completed")
                            last_progress = current_time
                            
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    print(f"Error processing Redis message: {e}")
                    
    except Exception as e:
        print(f"Redis monitoring error: {e}")
    finally:
        pubsub.unsubscribe()
        redis_client.close()
    
    # Mark any remaining as timeout
    for eval_id in eval_ids:
        if eval_id not in completed:
            result = results_dict[eval_id]
            # Check if not already in a terminal state
            if result.status not in TERMINAL_STATES:
                result.status = "timeout"
                result.error = "Redis monitoring timeout"
                if result.submit_timestamp:
                    result.total_duration = time.time() - result.submit_timestamp
    
    # Final verification: Check actual status from storage for any non-terminal states
    # This handles cases where events arrived out of order
    print(f"\n🔍 Verifying final states...")
    for eval_id, result in results_dict.items():
        if eval_id.startswith("failed_"):
            continue  # Skip failed submissions
            
        if result.status not in TERMINAL_STATES:
            try:
                # Quick HTTP check of actual status
                response = requests.get(f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}", timeout=2)
                if response.status_code == 200:
                    actual_status = response.json().get("status", result.status)
                    if actual_status != result.status:
                        print(f"  Status correction: {eval_id} {result.status} → {actual_status}")
                        result.status = actual_status
                        
                        # If it's now in a terminal state, update the completion time
                        if actual_status in TERMINAL_STATES:
                            result.total_duration = time.time() - result.submit_timestamp
                            completed.add(eval_id)
            except:
                pass  # Keep the status we have if verification fails


def run_rate_aware_load_test(
    concurrent_count: int,
    total_evaluations: int,
    duration_seconds: int = None,
    monitor_timeout: int = 300
):
    """
    Run load test that respects rate limits.
    
    Args:
        concurrent_count: Number of concurrent threads
        total_evaluations: Total evaluations to submit
        duration_seconds: If set, run for this duration instead of fixed count
        monitor_timeout: Maximum time to wait for evaluations to complete (seconds)
    """
    print(f"\n{'=' * 60}")
    print(f"RATE-AWARE LOAD TEST")
    print(f"Concurrent threads: {concurrent_count}")
    if duration_seconds:
        print(f"Duration: {duration_seconds} seconds")
    else:
        print(f"Total evaluations: {total_evaluations}")
    print(f"Rate limit: {MAX_REQUESTS_PER_SECOND} req/s (burst: {BURST_ALLOWANCE})")
    print(f"{'=' * 60}\n")
    
    # Generate test codes
    test_codes = []
    code_types = [
        ("Fast", "print('Fast eval {}')"),
        ("Medium", "import time\nprint('Medium eval {}')\ntime.sleep(1)"),
        ("Slow", "import time\nprint('Slow eval {}')\nfor i in range(3):\n    time.sleep(0.5)\n    print(f'Step {{i}}')")
    ]
    
    # Create evaluation codes
    if duration_seconds:
        # For duration-based tests, create a large pool of codes
        total_evaluations = duration_seconds * MAX_REQUESTS_PER_SECOND * 2
    
    for i in range(total_evaluations):
        code_type, template = code_types[i % len(code_types)]
        test_codes.append((code_type, template.format(i)))
    
    # Phase 1: Submit evaluations
    print(f"📤 Phase 1: Submitting {len(test_codes)} evaluations...")
    results_dict: Dict[str, LoadTestResult] = {}
    eval_ids = []
    start_time = time.time()
    end_time = start_time + duration_seconds if duration_seconds else None
    
    with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
        # Submit tasks
        futures = []
        submitted = 0
        
        for i, (code_type, code) in enumerate(test_codes):
            if end_time and time.time() >= end_time:
                break
                
            future = executor.submit(submit_evaluation, i, code)
            futures.append((future, code_type, i))
            submitted += 1
            
            # Progress update
            if submitted % 10 == 0:
                elapsed = time.time() - start_time
                rate = submitted / elapsed if elapsed > 0 else 0
                print(f"  Submitted: {submitted} | Rate: {rate:.1f} req/s")
        
        # Collect submission results
        for future, code_type, index in futures:
            try:
                eval_id, result = future.result(timeout=10)
                result.code_type = code_type
                
                if eval_id:  # Successfully submitted
                    results_dict[eval_id] = result
                    eval_ids.append(eval_id)
                else:  # Failed to submit
                    # Still track the failure
                    results_dict[f"failed_{index}"] = result
                    
            except Exception as e:
                print(f"Error collecting submission result: {e}")
    
    submission_time = time.time() - start_time
    print(f"\n✅ Submission phase complete: {len(eval_ids)} successful, {len(results_dict) - len(eval_ids)} failed")
    print(f"   Time: {submission_time:.1f}s, Rate: {len(eval_ids)/submission_time:.1f} submissions/s")
    
    # Phase 2: Monitor evaluations
    if eval_ids:  # Only monitor if we have successful submissions
        monitor_start = time.time()
        
        # Adjust monitor timeout based on load
        adjusted_timeout = monitor_timeout
        if len(eval_ids) > 20:
            # Add 2 seconds per evaluation over 20
            adjusted_timeout = monitor_timeout + (len(eval_ids) - 20) * 2
            print(f"  Adjusted monitor timeout: {adjusted_timeout}s (based on {len(eval_ids)} evaluations)")
        
        if MONITOR_MODE == "redis":
            print(f"\n📡 Phase 2: Monitoring via Redis pub/sub...")
            # Pass only successfully submitted evaluations
            successful_results = {eid: results_dict[eid] for eid in eval_ids}
            monitor_evaluations_redis(successful_results, timeout=adjusted_timeout)
        elif MONITOR_MODE == "batch":
            # Use batch monitoring to reduce load
            monitor_evaluations_batch(eval_ids, results_dict, timeout=adjusted_timeout)
        else:
            # For small loads, use individual monitoring with adaptive waiting
            if len(eval_ids) <= 10:
                print(f"\n📊 Phase 2: Monitoring via individual HTTP polling...")
                with ThreadPoolExecutor(max_workers=min(5, len(eval_ids))) as executor:
                    monitor_futures = []
                    for eval_id in eval_ids:
                        result = results_dict[eval_id]
                        # Increase individual timeout based on total load
                        individual_timeout = 120 + len(eval_ids) * 2
                        future = executor.submit(monitor_evaluation_http, eval_id, result, timeout=individual_timeout)
                        monitor_futures.append((future, eval_id))
                    
                    # Collect monitoring results
                    completed = 0
                    for future, eval_id in monitor_futures:
                        try:
                            # Give extra time for the future to complete
                            future_timeout = individual_timeout + 30
                            updated_result = future.result(timeout=future_timeout)
                            results_dict[eval_id] = updated_result
                            completed += 1
                            
                            if completed % 5 == 0:
                                print(f"  Monitored: {completed}/{len(eval_ids)}")
                        except Exception as e:
                            print(f"Error monitoring {eval_id}: {e}")
                            # Mark as timeout in results
                            if eval_id in results_dict:
                                results_dict[eval_id].status = "timeout"
                                results_dict[eval_id].error = f"Monitor error: {str(e)}"
            else:
                # For larger loads, use batch monitoring
                print(f"\n📊 Phase 2: Using batch monitoring for {len(eval_ids)} evaluations...")
                monitor_evaluations_batch(eval_ids, results_dict, timeout=adjusted_timeout)
        
        monitor_time = time.time() - monitor_start
        print(f"\n✅ Monitoring phase complete in {monitor_time:.1f}s")
    
    # Convert dict to list for compatibility with existing analysis
    results = list(results_dict.values())
    
    total_time = time.time() - start_time
    
    # Analyze results
    successful = [r for r in results if r.status == "completed"]
    failed = [r for r in results if r.status == "failed"]
    errors = [r for r in results if r.status in ["error", "timeout"]]
    rate_limited = [r for r in results if r.rate_limited]
    
    # Calculate metrics
    metrics = {
        "test_duration": total_time,
        "total_submitted": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "errors": len(errors),
        "rate_limited": len(rate_limited),
        "effective_rate": len(results) / total_time if total_time > 0 else 0,
        "success_rate": len(successful) / len(results) if results else 0,
    }
    
    if successful:
        submit_times = [r.submit_time for r in successful]
        complete_times = [r.total_duration for r in successful]
        queue_times = [r.queue_time for r in successful if r.queue_time > 0]
        exec_times = [r.execution_time for r in successful if r.execution_time > 0]
        wait_times = [r.wait_time for r in successful]
        
        metrics.update({
            "submit_time": {
                "min": min(submit_times),
                "max": max(submit_times),
                "avg": statistics.mean(submit_times),
                "median": statistics.median(submit_times),
            },
            "complete_time": {
                "min": min(complete_times),
                "max": max(complete_times),
                "avg": statistics.mean(complete_times),
                "median": statistics.median(complete_times),
            },
            "queue_time": {
                "min": min(queue_times) if queue_times else 0,
                "max": max(queue_times) if queue_times else 0,
                "avg": statistics.mean(queue_times) if queue_times else 0,
                "median": statistics.median(queue_times) if queue_times else 0,
            },
            "execution_time": {
                "min": min(exec_times) if exec_times else 0,
                "max": max(exec_times) if exec_times else 0,
                "avg": statistics.mean(exec_times) if exec_times else 0,
                "median": statistics.median(exec_times) if exec_times else 0,
            },
            "rate_limit_wait": {
                "total": sum(wait_times),
                "avg": statistics.mean(wait_times),
                "max": max(wait_times),
            }
        })
    
    # Print summary
    print(f"\n{'=' * 60}")
    print("RESULTS SUMMARY")
    print(f"{'=' * 60}")
    print(f"Test Duration: {total_time:.2f}s")
    print(f"Total Submitted: {metrics['total_submitted']}")
    print(f"Successful: {metrics['successful']} ({metrics['success_rate']*100:.1f}%)")
    print(f"Failed: {metrics['failed']}")
    print(f"Errors: {metrics['errors']}")
    print(f"Rate Limited: {metrics['rate_limited']}")
    print(f"Effective Rate: {metrics['effective_rate']:.2f} req/s")
    
    if successful:
        print("\nTiming Metrics:")
        print("  Submit Time:")
        print(f"    Avg: {metrics['submit_time']['avg']:.3f}s")
        print(f"    Median: {metrics['submit_time']['median']:.3f}s")
        
        print("  Queue Time:")
        print(f"    Avg: {metrics['queue_time']['avg']:.3f}s")
        print(f"    Max: {metrics['queue_time']['max']:.3f}s")
        
        print("  Execution Time:")
        print(f"    Avg: {metrics['execution_time']['avg']:.3f}s")
        print(f"    Median: {metrics['execution_time']['median']:.3f}s")
        
        print("  Total Completion Time:")
        print(f"    Avg: {metrics['complete_time']['avg']:.3f}s")
        print(f"    Max: {metrics['complete_time']['max']:.3f}s")
        
        print(f"\nRate Limiting:")
        print(f"  Total wait time: {metrics['rate_limit_wait']['total']:.1f}s")
        print(f"  Avg wait per request: {metrics['rate_limit_wait']['avg']:.3f}s")
    
    # Save results
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"load_test_{int(time.time())}.json"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "concurrent_threads": concurrent_count,
                "rate_limit": MAX_REQUESTS_PER_SECOND,
                "burst": BURST_ALLOWANCE,
            },
            "metrics": metrics,
            "evaluations": [
                {
                    "eval_id": r.eval_id,
                    "status": r.status,
                    "code_type": getattr(r, 'code_type', 'unknown'),
                    "submit_time": r.submit_time,
                    "queue_time": r.queue_time,
                    "execution_time": r.execution_time,
                    "total_duration": r.total_duration,
                    "wait_time": r.wait_time,
                    "error": r.error,
                }
                for r in results
            ],
        }, f, indent=2)
    
    print(f"\nDetailed results saved to {filepath}")
    
    return metrics


def run_sustained_load_test(duration_seconds: int = 60):
    """Run a sustained load test for a fixed duration."""
    print(f"\n{'=' * 60}")
    print(f"SUSTAINED LOAD TEST")
    print(f"Duration: {duration_seconds} seconds")
    print(f"Target rate: {MAX_REQUESTS_PER_SECOND} req/s")
    print(f"{'=' * 60}\n")
    
    # Use enough threads to saturate the rate limit
    concurrent_threads = min(20, MAX_REQUESTS_PER_SECOND * 2)
    
    metrics = run_rate_aware_load_test(
        concurrent_count=concurrent_threads,
        total_evaluations=0,  # Not used with duration
        duration_seconds=duration_seconds
    )
    
    # Additional analysis for sustained tests
    if metrics['successful'] > 0:
        print(f"\nSustained Performance:")
        print(f"  Average throughput: {metrics['successful'] / duration_seconds:.2f} successful/s")
        print(f"  Queue buildup: max {metrics['queue_time']['max']:.1f}s")
        print(f"  Success rate: {metrics['success_rate']*100:.1f}%")


# Pytest integration
@pytest.mark.performance
@pytest.mark.integration
@pytest.mark.load
@pytest.mark.kubernetes
@pytest.mark.parametrize("concurrent,total,expected_success_rate", [
    (5, 10, 0.9),    # Small test - expect 90%+ success
    (10, 20, 0.9),   # Medium test - expect 90%+ success
])
def test_load_rate_aware(concurrent, total, expected_success_rate):
    """Pytest wrapper for load testing."""
    # Use shorter timeout for automated tests
    metrics = run_rate_aware_load_test(concurrent, total, monitor_timeout=120)
    
    # Assertions
    assert metrics["success_rate"] >= expected_success_rate, \
        f"Success rate {metrics['success_rate']} below expected {expected_success_rate}"
    
    # Check that rate limiting worked
    assert metrics["effective_rate"] <= MAX_REQUESTS_PER_SECOND * 1.2, \
        f"Effective rate {metrics['effective_rate']} exceeded rate limit"


@pytest.mark.performance
@pytest.mark.integration
@pytest.mark.load
@pytest.mark.slow
@pytest.mark.kubernetes
def test_large_load():
    """Larger load test - marked as slow."""
    metrics = run_rate_aware_load_test(20, 50, monitor_timeout=300)
    assert metrics["success_rate"] >= 0.9


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "sustained":
            duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            run_sustained_load_test(duration)
        else:
            concurrent = int(sys.argv[1])
            total = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            timeout = int(sys.argv[3]) if len(sys.argv) > 3 else 300
            print(f"Using monitor timeout: {timeout}s") if len(sys.argv) > 3 else None
            run_rate_aware_load_test(concurrent, total, monitor_timeout=timeout)
    else:
        # Default: rate-aware test with 20 threads, 100 evaluations
        print("Usage: python test_load_rate_aware.py <concurrent> <total> [timeout]")
        print("       python test_load_rate_aware.py sustained [duration]")
        print("\nRunning default: 20 concurrent, 100 total")
        run_rate_aware_load_test(20, 100)