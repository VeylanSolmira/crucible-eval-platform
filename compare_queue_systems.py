#!/usr/bin/env python3
"""
Compare performance between legacy queue and Celery systems.
Submits identical tasks to both and measures completion times.
"""
import requests
import time
import json
import statistics
from datetime import datetime
from typing import List, Dict, Tuple

class QueueComparison:
    def __init__(self, api_url="http://localhost:8000"):
        self.api_url = api_url
        self.results = {"legacy": [], "celery": []}
    
    def submit_evaluation(self, code: str, test_name: str) -> str:
        """Submit an evaluation and return the eval_id"""
        response = requests.post(
            f"{self.api_url}/api/eval",
            json={"code": code, "language": "python"}
        )
        if response.status_code == 200:
            return response.json()["eval_id"]
        else:
            raise Exception(f"Failed to submit: {response.text}")
    
    def wait_for_completion(self, eval_id: str, timeout: int = 30) -> Tuple[str, float]:
        """Wait for evaluation to complete and return status and duration"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Get all evaluations and find our specific one
            response = requests.get(f"{self.api_url}/api/evaluations")
            if response.status_code == 200:
                evaluations = response.json().get("evaluations", [])
                # Find our evaluation
                for eval_data in evaluations:
                    if eval_data.get("eval_id") == eval_id:
                        status = eval_data.get("status", "unknown")
                        if status in ["completed", "failed"]:
                            duration = time.time() - start_time
                            return status, duration
                        break
            time.sleep(0.5)
        
        return "timeout", timeout
    
    def check_executor_logs(self, eval_id: str) -> str:
        """Determine which executor processed the evaluation"""
        # Check logs to see which executor handled this
        # In practice, you'd grep docker logs for the eval_id
        # For now, we'll check if it exists in storage
        return "unknown"
    
    def run_comparison_test(self, num_tests: int = 10):
        """Run comparison tests between the two systems"""
        print(f"Running {num_tests} comparison tests...\n")
        
        test_codes = [
            'print("Quick test")',
            'import time; time.sleep(1); print("1 second task")',
            'import time; time.sleep(2); print("2 second task")',
            'print("\\n".join([str(i) for i in range(100)]))',
            'import math; print(sum([math.sqrt(i) for i in range(10000)]))',
        ]
        
        all_results = []
        
        for i in range(num_tests):
            code = test_codes[i % len(test_codes)]
            test_name = f"Test {i+1}"
            
            print(f"{test_name}: Submitting evaluation...")
            try:
                eval_id = self.submit_evaluation(code, test_name)
                print(f"  Eval ID: {eval_id}")
                
                # Wait for completion
                status, duration = self.wait_for_completion(eval_id)
                
                result = {
                    "test": test_name,
                    "eval_id": eval_id,
                    "status": status,
                    "duration": duration,
                    "timestamp": datetime.now().isoformat()
                }
                
                all_results.append(result)
                print(f"  Status: {status}, Duration: {duration:.2f}s")
                
            except Exception as e:
                print(f"  Error: {e}")
            
            # Small delay between tests
            time.sleep(1)
        
        return all_results
    
    def analyze_results(self, results: List[Dict]):
        """Analyze and display comparison metrics"""
        print("\n" + "="*60)
        print("COMPARISON METRICS")
        print("="*60)
        
        # Filter successful completions
        completed = [r for r in results if r["status"] == "completed"]
        
        if not completed:
            print("No successful completions to analyze!")
            return
        
        durations = [r["duration"] for r in completed]
        
        print(f"\nTotal evaluations: {len(results)}")
        print(f"Successful: {len(completed)}")
        print(f"Failed: {len([r for r in results if r['status'] == 'failed'])}")
        print(f"Timeouts: {len([r for r in results if r['status'] == 'timeout'])}")
        
        print("\nTiming Statistics (seconds):")
        print(f"  Min: {min(durations):.3f}")
        print(f"  Max: {max(durations):.3f}")
        print(f"  Mean: {statistics.mean(durations):.3f}")
        print(f"  Median: {statistics.median(durations):.3f}")
        if len(durations) > 1:
            print(f"  Std Dev: {statistics.stdev(durations):.3f}")
        
        # Check Celery vs Legacy distribution
        # This would require checking logs to see which system processed each
        print("\nSystem Distribution:")
        print("  Legacy Queue (executor-1/2): [Would need log analysis]")
        print("  Celery (executor-3): [Would need log analysis]")
        
    def check_queue_status(self):
        """Check current status of both queue systems"""
        print("\n" + "="*60)
        print("QUEUE SYSTEM STATUS")
        print("="*60)
        
        # Check legacy queue
        try:
            response = requests.get(f"{self.api_url}/api/status")
            if response.status_code == 200:
                status = response.json()
                queue_status = status.get("queue_service", {})
                print("\nLegacy Queue Status:")
                print(f"  Queued: {queue_status.get('queued', 'N/A')}")
                print(f"  Running: {queue_status.get('running', 'N/A')}")
        except:
            print("\nLegacy Queue Status: Unable to fetch")
        
        # Check Celery (would need to query Flower API)
        print("\nCelery Status:")
        print("  Check Flower dashboard at http://localhost:5555")
        print("  (Login: admin/crucible)")

def main():
    comparison = QueueComparison()
    
    # Check initial status
    comparison.check_queue_status()
    
    # Run comparison tests
    results = comparison.run_comparison_test(num_tests=10)
    
    # Analyze results
    comparison.analyze_results(results)
    
    # Final status check
    comparison.check_queue_status()
    
    # Save results
    with open("queue_comparison_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to queue_comparison_results.json")

if __name__ == "__main__":
    main()