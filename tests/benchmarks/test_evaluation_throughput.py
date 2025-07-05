#!/usr/bin/env python3
"""
Concurrent Evaluation Throughput Test

This benchmark measures how many code evaluations the platform can handle
per minute under sustained load. It tests the entire critical path:
API → Celery → Executor → Storage

Key metrics:
- Evaluations per minute (throughput)
- Latency percentiles (p50, p95, p99)
- Queue depth over time
- Executor utilization
- Error rate under load
"""

import time
import json
import statistics
import threading
import queue
from datetime import datetime
from typing import List, Dict, Any
import requests
import redis

# Import shared test configuration
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from conftest import get_api_url, get_request_config

# Configuration
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
TARGET_RPS = 2  # Target requests per second (start conservative)
TEST_DURATION_SECONDS = 60  # Run for 1 minute
WARMUP_SECONDS = 5  # Warmup period before measurements

# Test workloads - mix of quick and slow evaluations
TEST_WORKLOADS = [
    {
        "name": "quick",
        "code": "print('Quick evaluation'); result = sum(range(100))",
        "weight": 0.6  # 60% of requests
    },
    {
        "name": "medium", 
        "code": "import time; time.sleep(1); print('Medium evaluation')",
        "weight": 0.3  # 30% of requests
    },
    {
        "name": "compute",
        "code": "import math; result = [math.sqrt(i) for i in range(10000)]; print(f'Computed {len(result)} values')",
        "weight": 0.1  # 10% of requests
    }
]


class ThroughputTest:
    def __init__(self):
        self.metrics = {
            "evaluations_submitted": 0,
            "evaluations_completed": 0,
            "evaluations_failed": 0,
            "submission_errors": 0,
            "latencies": [],
            "queue_depths": [],
            "executor_utilization": [],
            "timestamps": {
                "start": None,
                "end": None
            }
        }
        self.redis_client = redis.from_url(REDIS_URL)
        self.active_evaluations = {}
        self.results_queue = queue.Queue()
        self.stop_event = threading.Event()
        
    def select_workload(self) -> Dict[str, Any]:
        """Select a workload based on weights"""
        import random
        rand = random.random()
        cumulative = 0
        
        for workload in TEST_WORKLOADS:
            cumulative += workload["weight"]
            if rand <= cumulative:
                return workload
        
        return TEST_WORKLOADS[0]  # Fallback
    
    def submit_evaluation(self) -> bool:
        """Submit a single evaluation and track it"""
        workload = self.select_workload()
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{get_api_url()}/eval",
                json={
                    "code": workload["code"],
                    "language": "python",
                    "timeout": 30
                },
                **get_request_config()
            )
            
            if response.status_code == 200:
                eval_id = response.json()["eval_id"]
                self.active_evaluations[eval_id] = {
                    "start_time": start_time,
                    "workload": workload["name"]
                }
                self.metrics["evaluations_submitted"] += 1
                return True
            else:
                self.metrics["submission_errors"] += 1
                return False
                
        except Exception as e:
            print(f"❌ Submission error: {e}")
            self.metrics["submission_errors"] += 1
            return False
    
    def check_evaluation_status(self, eval_id: str) -> bool:
        """Check if an evaluation is complete"""
        try:
            response = requests.get(
                f"{get_api_url()}/eval/{eval_id}",
                **get_request_config()
            )
            
            if response.status_code == 200:
                result = response.json()
                status = result.get("status")
                
                if status in ["completed", "failed"]:
                    # Calculate latency
                    start_time = self.active_evaluations[eval_id]["start_time"]
                    latency = time.time() - start_time
                    self.metrics["latencies"].append(latency)
                    
                    if status == "completed":
                        self.metrics["evaluations_completed"] += 1
                    else:
                        self.metrics["evaluations_failed"] += 1
                    
                    return True
            
            return False
            
        except Exception:
            return False
    
    def monitor_system_metrics(self):
        """Monitor queue depth and executor utilization"""
        try:
            # Check Redis queue depth (Celery default queue)
            queue_depth = self.redis_client.llen("celery")
            self.metrics["queue_depths"].append(queue_depth)
            
            # Check executor utilization
            available = self.redis_client.llen("executors:available")
            busy_keys = list(self.redis_client.scan_iter(match="executor:busy:*"))
            total_executors = available + len(busy_keys)
            
            if total_executors > 0:
                utilization = (len(busy_keys) / total_executors) * 100
                self.metrics["executor_utilization"].append(utilization)
            
        except Exception as e:
            print(f"⚠️  Error monitoring metrics: {e}")
    
    def submission_worker(self):
        """Worker thread that submits evaluations at target rate"""
        interval = 1.0 / TARGET_RPS
        
        while not self.stop_event.is_set():
            start = time.time()
            self.submit_evaluation()
            
            # Sleep to maintain target rate
            elapsed = time.time() - start
            if elapsed < interval:
                time.sleep(interval - elapsed)
    
    def monitoring_worker(self):
        """Worker thread that monitors completion and system metrics"""
        while not self.stop_event.is_set():
            # Check active evaluations for completion
            completed = []
            for eval_id in list(self.active_evaluations.keys()):
                if self.check_evaluation_status(eval_id):
                    completed.append(eval_id)
            
            # Remove completed evaluations
            for eval_id in completed:
                del self.active_evaluations[eval_id]
            
            # Monitor system metrics
            self.monitor_system_metrics()
            
            time.sleep(1)  # Check every second
    
    def run_test(self):
        """Run the throughput test"""
        print("\n" + "="*60)
        print("CONCURRENT EVALUATION THROUGHPUT TEST")
        print("="*60)
        print(f"Target Rate: {TARGET_RPS} evaluations/second")
        print(f"Test Duration: {TEST_DURATION_SECONDS} seconds")
        print(f"Warmup Period: {WARMUP_SECONDS} seconds")
        print("\nWorkload Mix:")
        for workload in TEST_WORKLOADS:
            print(f"  - {workload['name']}: {workload['weight']*100:.0f}%")
        print("\n" + "-"*60)
        
        # Start worker threads
        submission_thread = threading.Thread(target=self.submission_worker)
        monitoring_thread = threading.Thread(target=self.monitoring_worker)
        
        submission_thread.start()
        monitoring_thread.start()
        
        # Warmup period
        print(f"\n⏳ Warming up for {WARMUP_SECONDS} seconds...")
        time.sleep(WARMUP_SECONDS)
        
        # Reset metrics after warmup
        self.metrics = {
            "evaluations_submitted": 0,
            "evaluations_completed": 0,
            "evaluations_failed": 0,
            "submission_errors": 0,
            "latencies": [],
            "queue_depths": [],
            "executor_utilization": [],
            "timestamps": {
                "start": datetime.now().isoformat(),
                "end": None
            }
        }
        
        # Run test
        print(f"\n🚀 Running test for {TEST_DURATION_SECONDS} seconds...")
        start_time = time.time()
        
        # Progress updates
        while time.time() - start_time < TEST_DURATION_SECONDS:
            elapsed = int(time.time() - start_time)
            print(f"\r⏱️  Progress: {elapsed}/{TEST_DURATION_SECONDS}s | "
                  f"Submitted: {self.metrics['evaluations_submitted']} | "
                  f"Completed: {self.metrics['evaluations_completed']}", 
                  end="", flush=True)
            time.sleep(1)
        
        print("\n\n⏹️  Stopping load generation...")
        self.stop_event.set()
        
        # Wait for threads to finish
        submission_thread.join()
        
        # Wait for remaining evaluations to complete (max 30s)
        print("⏳ Waiting for remaining evaluations to complete...")
        wait_start = time.time()
        while self.active_evaluations and time.time() - wait_start < 30:
            time.sleep(1)
            print(f"\r📊 Remaining active evaluations: {len(self.active_evaluations)}", 
                  end="", flush=True)
        
        monitoring_thread.join()
        
        self.metrics["timestamps"]["end"] = datetime.now().isoformat()
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate and display the test report"""
        print("\n\n" + "="*60)
        print("TEST RESULTS")
        print("="*60)
        
        # Calculate derived metrics
        test_duration = TEST_DURATION_SECONDS
        throughput = self.metrics["evaluations_completed"] / test_duration * 60
        
        print(f"\n📊 Throughput Metrics:")
        print(f"  - Evaluations Submitted: {self.metrics['evaluations_submitted']}")
        print(f"  - Evaluations Completed: {self.metrics['evaluations_completed']}")
        print(f"  - Evaluations Failed: {self.metrics['evaluations_failed']}")
        print(f"  - Submission Errors: {self.metrics['submission_errors']}")
        print(f"  - Throughput: {throughput:.1f} evaluations/minute")
        
        if self.metrics["latencies"]:
            latencies = sorted(self.metrics["latencies"])
            p50 = latencies[len(latencies)//2]
            p95 = latencies[int(len(latencies)*0.95)]
            p99 = latencies[int(len(latencies)*0.99)] if len(latencies) > 100 else latencies[-1]
            
            print(f"\n⏱️  Latency Metrics:")
            print(f"  - Min: {min(latencies):.2f}s")
            print(f"  - P50: {p50:.2f}s")
            print(f"  - P95: {p95:.2f}s")
            print(f"  - P99: {p99:.2f}s")
            print(f"  - Max: {max(latencies):.2f}s")
            print(f"  - Average: {statistics.mean(latencies):.2f}s")
        
        if self.metrics["queue_depths"]:
            print(f"\n📥 Queue Metrics:")
            print(f"  - Max Queue Depth: {max(self.metrics['queue_depths'])}")
            print(f"  - Avg Queue Depth: {statistics.mean(self.metrics['queue_depths']):.1f}")
        
        if self.metrics["executor_utilization"]:
            print(f"\n🖥️  Executor Metrics:")
            print(f"  - Max Utilization: {max(self.metrics['executor_utilization']):.1f}%")
            print(f"  - Avg Utilization: {statistics.mean(self.metrics['executor_utilization']):.1f}%")
        
        # Success criteria evaluation
        print(f"\n✅ Success Criteria:")
        success_criteria = {
            "Throughput ≥ 100/min": throughput >= 100,
            "P95 Latency ≤ 30s": p95 <= 30 if self.metrics["latencies"] else False,
            "No Evaluation Losses": self.metrics["evaluations_failed"] == 0,
            "Submission Success Rate ≥ 99%": (self.metrics["evaluations_submitted"] / 
                (self.metrics["evaluations_submitted"] + self.metrics["submission_errors"]) * 100) >= 99
                if self.metrics["evaluations_submitted"] > 0 else False
        }
        
        all_passed = True
        for criterion, passed in success_criteria.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  - {criterion}: {status}")
            if not passed:
                all_passed = False
        
        # Save detailed metrics
        with open("throughput_test_results.json", "w") as f:
            json.dump(self.metrics, f, indent=2)
        
        print(f"\n📄 Detailed metrics saved to: throughput_test_results.json")
        
        # Final verdict
        print("\n" + "="*60)
        if all_passed:
            print("🎉 THROUGHPUT TEST PASSED!")
        else:
            print("❌ THROUGHPUT TEST FAILED - Performance improvements needed")
        print("="*60)
        
        # Exit with appropriate code
        sys.exit(0 if all_passed else 1)


def main():
    """Run the throughput test"""
    test = ThroughputTest()
    test.run_test()


if __name__ == "__main__":
    main()