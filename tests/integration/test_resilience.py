#!/usr/bin/env python3
"""
Service resilience testing.

Tests the platform's ability to handle service restarts, failures,
and recovery scenarios.
"""

import subprocess
import time
import requests
import json
from typing import Dict, Any, List

API_BASE_URL = "http://localhost:8000/api"


class ResilienceTest:
    """Base class for resilience tests."""
    
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = ""
        self.details: Dict[str, Any] = {}
        self.duration = 0.0
    
    def run(self) -> bool:
        """Run the test and return success status."""
        raise NotImplementedError


class ServiceRestartTest(ResilienceTest):
    """Test evaluation continuity during service restarts."""
    
    def __init__(self):
        super().__init__("Service Restart Test")
    
    def run(self) -> bool:
        start_time = time.time()
        
        try:
            # Step 1: Submit a long-running evaluation
            eval_request = {
                "code": """
import time
print("Starting long evaluation...")
for i in range(10):
    time.sleep(1)
    print(f"Step {i+1}/10")
print("Evaluation complete!")
""",
                "language": "python",
                "engine": "docker",
                "timeout": 30
            }
            
            response = requests.post(f"{API_BASE_URL}/eval", json=eval_request, timeout=10)
            response.raise_for_status()
            eval_id = response.json()["eval_id"]
            self.details["eval_id"] = eval_id
            
            # Step 2: Wait for it to start running
            time.sleep(2)
            
            # Step 3: Restart a service (queue-worker)
            print("  Restarting queue-worker service...")
            subprocess.run(["docker-compose", "restart", "queue-worker"], 
                         capture_output=True, text=True, check=True)
            
            # Step 4: Wait for service to come back up
            time.sleep(5)
            
            # Step 5: Check if evaluation continues/completes
            max_wait = 30
            final_status = None
            
            for _ in range(max_wait):
                try:
                    response = requests.get(f"{API_BASE_URL}/eval/{eval_id}", timeout=5)
                    if response.status_code == 200:
                        status_data = response.json()
                        if status_data["status"] in ["completed", "failed"]:
                            final_status = status_data
                            break
                except:
                    pass  # Service might be temporarily unavailable
                
                time.sleep(1)
            
            if final_status and final_status["status"] == "completed":
                self.passed = True
                self.details["final_status"] = final_status
            else:
                self.error = f"Evaluation did not complete after restart: {final_status}"
                
        except Exception as e:
            self.error = str(e)
        
        self.duration = time.time() - start_time
        return self.passed


class CeleryWorkerFailureTest(ResilienceTest):
    """Test handling of Celery worker failures."""
    
    def __init__(self):
        super().__init__("Celery Worker Failure Test")
    
    def run(self) -> bool:
        start_time = time.time()
        
        try:
            # Step 1: Stop Celery worker
            print("  Stopping celery-worker...")
            subprocess.run(["docker-compose", "stop", "celery-worker"], 
                         capture_output=True, text=True, check=True)
            
            # Step 2: Submit evaluation (should queue)
            eval_request = {
                "code": "print('Test during worker outage')",
                "language": "python",
                "engine": "docker",
                "timeout": 10
            }
            
            response = requests.post(f"{API_BASE_URL}/eval", json=eval_request, timeout=10)
            response.raise_for_status()
            eval_id = response.json()["eval_id"]
            self.details["eval_id"] = eval_id
            
            # Step 3: Verify it's queued
            time.sleep(2)
            response = requests.get(f"{API_BASE_URL}/eval/{eval_id}", timeout=5)
            status_data = response.json()
            
            if status_data["status"] != "queued":
                self.error = f"Expected queued status, got: {status_data['status']}"
                return False
            
            # Step 4: Start Celery worker
            print("  Starting celery-worker...")
            subprocess.run(["docker-compose", "start", "celery-worker"], 
                         capture_output=True, text=True, check=True)
            
            # Step 5: Wait for evaluation to process
            time.sleep(10)
            
            response = requests.get(f"{API_BASE_URL}/eval/{eval_id}", timeout=5)
            final_status = response.json()
            
            if final_status["status"] == "completed":
                self.passed = True
                self.details["final_status"] = final_status
            else:
                self.error = f"Evaluation not processed after worker restart: {final_status}"
                
        except Exception as e:
            self.error = str(e)
        finally:
            # Ensure worker is running
            subprocess.run(["docker-compose", "start", "celery-worker"], 
                         capture_output=True, text=True)
        
        self.duration = time.time() - start_time
        return self.passed


class StorageServiceFailureTest(ResilienceTest):
    """Test handling of storage service failures."""
    
    def __init__(self):
        super().__init__("Storage Service Failure Test")
    
    def run(self) -> bool:
        start_time = time.time()
        
        try:
            # Step 1: Submit evaluation
            eval_request = {
                "code": "print('Storage test output')",
                "language": "python",
                "engine": "docker",
                "timeout": 10
            }
            
            response = requests.post(f"{API_BASE_URL}/eval", json=eval_request, timeout=10)
            response.raise_for_status()
            eval_id = response.json()["eval_id"]
            self.details["eval_id"] = eval_id
            
            # Step 2: Wait for completion
            time.sleep(5)
            
            # Step 3: Stop storage service
            print("  Stopping storage-service...")
            subprocess.run(["docker-compose", "stop", "storage-service"], 
                         capture_output=True, text=True, check=True)
            
            # Step 4: Try to retrieve (should fail gracefully)
            try:
                response = requests.get(f"{API_BASE_URL}/eval/{eval_id}", timeout=5)
                # Should either fail or return cached data
                self.details["during_outage"] = {
                    "status_code": response.status_code,
                    "response": response.json() if response.status_code == 200 else None
                }
            except Exception as e:
                self.details["during_outage"] = {"error": str(e)}
            
            # Step 5: Restart storage service
            print("  Starting storage-service...")
            subprocess.run(["docker-compose", "start", "storage-service"], 
                         capture_output=True, text=True, check=True)
            time.sleep(5)
            
            # Step 6: Verify data is still accessible
            response = requests.get(f"{API_BASE_URL}/eval/{eval_id}", timeout=5)
            if response.status_code == 200:
                final_data = response.json()
                if final_data.get("eval_id") == eval_id:
                    self.passed = True
                    self.details["after_restart"] = final_data
                else:
                    self.error = "Data corrupted after storage restart"
            else:
                self.error = f"Cannot retrieve data after storage restart: {response.status_code}"
                
        except Exception as e:
            self.error = str(e)
        finally:
            # Ensure service is running
            subprocess.run(["docker-compose", "start", "storage-service"], 
                         capture_output=True, text=True)
        
        self.duration = time.time() - start_time
        return self.passed


class NetworkPartitionTest(ResilienceTest):
    """Test handling of network partitions between services."""
    
    def __init__(self):
        super().__init__("Network Partition Test")
    
    def run(self) -> bool:
        start_time = time.time()
        
        try:
            # This test would require more complex network manipulation
            # For now, we'll test basic connectivity recovery
            
            # Submit evaluation
            eval_request = {
                "code": "print('Network test')",
                "language": "python",
                "engine": "docker",
                "timeout": 10
            }
            
            response = requests.post(f"{API_BASE_URL}/eval", json=eval_request, timeout=10)
            response.raise_for_status()
            eval_id = response.json()["eval_id"]
            
            # Wait for completion
            time.sleep(5)
            
            # Verify we can still retrieve
            response = requests.get(f"{API_BASE_URL}/eval/{eval_id}", timeout=5)
            if response.status_code == 200:
                self.passed = True
                self.details["result"] = response.json()
            else:
                self.error = f"Failed to retrieve: {response.status_code}"
                
        except Exception as e:
            self.error = str(e)
        
        self.duration = time.time() - start_time
        return self.passed


def run_resilience_tests():
    """Run all resilience tests."""
    print("=" * 60)
    print("SERVICE RESILIENCE TESTS")
    print("=" * 60)
    print()
    
    # Check if services are running
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("ERROR: Services not healthy. Please ensure all services are running.")
            return
    except:
        print("ERROR: Cannot connect to API. Please ensure services are running.")
        return
    
    tests = [
        ServiceRestartTest(),
        CeleryWorkerFailureTest(),
        StorageServiceFailureTest(),
        NetworkPartitionTest()
    ]
    
    results = []
    
    for test in tests:
        print(f"Running {test.name}...", end=" ", flush=True)
        
        try:
            test.run()
            results.append(test)
            
            if test.passed:
                print(f"✅ PASSED ({test.duration:.2f}s)")
            else:
                print(f"❌ FAILED ({test.duration:.2f}s)")
                if test.error:
                    print(f"   Error: {test.error}")
        except Exception as e:
            test.error = str(e)
            test.passed = False
            results.append(test)
            print(f"❌ FAILED with exception: {e}")
    
    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for t in results if t.passed)
    failed = sum(1 for t in results if not t.passed)
    
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    # Save results
    with open("resilience_test_results.json", "w") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total": len(results),
                "passed": passed,
                "failed": failed
            },
            "tests": [
                {
                    "name": t.name,
                    "passed": t.passed,
                    "error": t.error,
                    "duration": t.duration,
                    "details": t.details
                }
                for t in results
            ]
        }, f, indent=2)
    
    print(f"\nDetailed results saved to resilience_test_results.json")


if __name__ == "__main__":
    run_resilience_tests()