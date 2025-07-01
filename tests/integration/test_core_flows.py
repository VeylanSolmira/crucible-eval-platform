#!/usr/bin/env python3
"""
Integration tests for core evaluation flows.

Tests the complete flow from submission to completion:
1. Frontend → API → Celery → Executor → Storage
2. Frontend → API → Storage retrieval
3. Error handling paths
"""

import asyncio
import json
import time
import requests
from typing import Dict, Any, Optional

# API base URL - can be overridden by environment variable
API_BASE_URL = "http://localhost:8000/api"


class TestResult:
    """Test result tracking"""
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error: Optional[str] = None
        self.duration: float = 0.0
        self.details: Dict[str, Any] = {}


def test_health_check() -> TestResult:
    """Test that all services are healthy."""
    result = TestResult("Health Check")
    start_time = time.time()
    
    try:
        # Check API health
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        response.raise_for_status()
        health_data = response.json()
        
        # Verify all components are healthy
        if health_data.get("status") != "healthy":
            raise Exception(f"API not healthy: {health_data}")
            
        # Check individual services
        services = health_data.get("services", {})
        for service, status in services.items():
            if not status.get("healthy", False):
                raise Exception(f"Service {service} not healthy: {status}")
        
        result.passed = True
        result.details = health_data
        
    except Exception as e:
        result.error = str(e)
    
    result.duration = time.time() - start_time
    return result


def test_submit_evaluation() -> TestResult:
    """Test submitting a simple evaluation."""
    result = TestResult("Submit Evaluation")
    start_time = time.time()
    
    try:
        # Submit evaluation
        eval_request = {
            "code": "print('Hello from integration test!')",
            "language": "python",
            "engine": "docker",
            "timeout": 30
        }
        
        response = requests.post(f"{API_BASE_URL}/eval", json=eval_request, timeout=10)
        response.raise_for_status()
        submit_data = response.json()
        
        # Verify we got an eval_id
        eval_id = submit_data.get("eval_id")
        if not eval_id:
            raise Exception(f"No eval_id returned: {submit_data}")
        
        result.details["eval_id"] = eval_id
        result.details["submit_response"] = submit_data
        result.passed = True
        
    except Exception as e:
        result.error = str(e)
    
    result.duration = time.time() - start_time
    return result


def test_evaluation_lifecycle() -> TestResult:
    """Test complete evaluation lifecycle from submission to completion."""
    result = TestResult("Evaluation Lifecycle")
    start_time = time.time()
    
    try:
        # Step 1: Submit evaluation
        eval_request = {
            "code": "import time\nprint('Starting...')\ntime.sleep(1)\nprint('Done!')",
            "language": "python",
            "engine": "docker",
            "timeout": 30
        }
        
        response = requests.post(f"{API_BASE_URL}/eval", json=eval_request, timeout=10)
        response.raise_for_status()
        eval_id = response.json()["eval_id"]
        result.details["eval_id"] = eval_id
        
        # Step 2: Poll for status updates
        max_polls = 30  # 30 seconds max
        poll_interval = 1
        final_status = None
        
        for i in range(max_polls):
            response = requests.get(f"{API_BASE_URL}/eval/{eval_id}", timeout=5)
            response.raise_for_status()
            status_data = response.json()
            
            current_status = status_data.get("status")
            result.details[f"poll_{i}"] = current_status
            
            if current_status in ["completed", "failed"]:
                final_status = status_data
                break
                
            time.sleep(poll_interval)
        
        if not final_status:
            raise Exception(f"Evaluation did not complete in {max_polls} seconds")
        
        # Step 3: Verify completion
        if final_status["status"] != "completed":
            raise Exception(f"Evaluation failed: {final_status}")
        
        # Verify output
        output = final_status.get("output", "")
        if "Starting..." not in output or "Done!" not in output:
            raise Exception(f"Unexpected output: {output}")
        
        result.details["final_status"] = final_status
        result.passed = True
        
    except Exception as e:
        result.error = str(e)
    
    result.duration = time.time() - start_time
    return result


def test_error_handling() -> TestResult:
    """Test error handling for various failure scenarios."""
    result = TestResult("Error Handling")
    start_time = time.time()
    
    try:
        # Test 1: Invalid code that should fail
        eval_request = {
            "code": "import sys\nsys.exit(1)",
            "language": "python",
            "engine": "docker",
            "timeout": 10
        }
        
        response = requests.post(f"{API_BASE_URL}/eval", json=eval_request, timeout=10)
        response.raise_for_status()
        eval_id = response.json()["eval_id"]
        
        # Wait for completion
        time.sleep(3)
        
        response = requests.get(f"{API_BASE_URL}/eval/{eval_id}", timeout=5)
        response.raise_for_status()
        status_data = response.json()
        
        if status_data["status"] != "failed":
            raise Exception(f"Expected failed status for error code, got: {status_data['status']}")
        
        result.details["error_test"] = status_data
        
        # Test 2: Invalid request
        bad_request = {"invalid": "request"}
        response = requests.post(f"{API_BASE_URL}/eval", json=bad_request, timeout=10)
        
        if response.status_code == 200:
            raise Exception("Expected 422 error for invalid request")
        
        result.details["invalid_request_status"] = response.status_code
        result.passed = True
        
    except Exception as e:
        result.error = str(e)
    
    result.duration = time.time() - start_time
    return result


def test_concurrent_evaluations() -> TestResult:
    """Test multiple concurrent evaluations."""
    result = TestResult("Concurrent Evaluations")
    start_time = time.time()
    
    try:
        # Submit 5 evaluations concurrently
        eval_ids = []
        for i in range(5):
            eval_request = {
                "code": f"import time\nprint('Eval {i}')\ntime.sleep(0.5)",
                "language": "python",
                "engine": "docker",
                "timeout": 30
            }
            
            response = requests.post(f"{API_BASE_URL}/eval", json=eval_request, timeout=10)
            response.raise_for_status()
            eval_ids.append(response.json()["eval_id"])
        
        result.details["submitted_count"] = len(eval_ids)
        result.details["eval_ids"] = eval_ids
        
        # Wait for all to complete
        time.sleep(5)
        
        # Check all completed successfully
        completed_count = 0
        for eval_id in eval_ids:
            response = requests.get(f"{API_BASE_URL}/eval/{eval_id}", timeout=5)
            if response.status_code == 200:
                status_data = response.json()
                if status_data["status"] == "completed":
                    completed_count += 1
        
        result.details["completed_count"] = completed_count
        
        if completed_count != len(eval_ids):
            raise Exception(f"Only {completed_count}/{len(eval_ids)} evaluations completed")
        
        result.passed = True
        
    except Exception as e:
        result.error = str(e)
    
    result.duration = time.time() - start_time
    return result


def test_storage_retrieval() -> TestResult:
    """Test storage retrieval functionality."""
    result = TestResult("Storage Retrieval")
    start_time = time.time()
    
    try:
        # First submit an evaluation
        eval_request = {
            "code": "print('Storage test output')",
            "language": "python",
            "engine": "docker",
            "timeout": 10
        }
        
        response = requests.post(f"{API_BASE_URL}/eval", json=eval_request, timeout=10)
        response.raise_for_status()
        eval_id = response.json()["eval_id"]
        
        # Wait for completion
        time.sleep(3)
        
        # Test direct storage retrieval
        response = requests.get(f"{API_BASE_URL}/storage/evaluation/{eval_id}", timeout=5)
        response.raise_for_status()
        storage_data = response.json()
        
        # Verify storage data
        if not storage_data.get("eval_id") == eval_id:
            raise Exception(f"Storage eval_id mismatch: {storage_data}")
        
        if "Storage test output" not in storage_data.get("output", ""):
            raise Exception(f"Output not stored correctly: {storage_data}")
        
        result.details["storage_data"] = storage_data
        result.passed = True
        
    except Exception as e:
        result.error = str(e)
    
    result.duration = time.time() - start_time
    return result


def run_all_tests():
    """Run all integration tests and report results."""
    print("=" * 60)
    print("CRUCIBLE PLATFORM INTEGRATION TESTS")
    print("=" * 60)
    print()
    
    tests = [
        test_health_check,
        test_submit_evaluation,
        test_evaluation_lifecycle,
        test_error_handling,
        test_concurrent_evaluations,
        test_storage_retrieval
    ]
    
    results = []
    total_duration = 0
    
    for test_func in tests:
        print(f"Running {test_func.__name__}...", end=" ", flush=True)
        result = test_func()
        results.append(result)
        total_duration += result.duration
        
        if result.passed:
            print(f"✅ PASSED ({result.duration:.2f}s)")
        else:
            print(f"❌ FAILED ({result.duration:.2f}s)")
            if result.error:
                print(f"   Error: {result.error}")
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total Duration: {total_duration:.2f}s")
    
    # Write detailed results to file
    with open("integration_test_results.json", "w") as f:
        test_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total": len(results),
                "passed": passed,
                "failed": failed,
                "duration": total_duration
            },
            "tests": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "error": r.error,
                    "duration": r.duration,
                    "details": r.details
                }
                for r in results
            ]
        }
        json.dump(test_data, f, indent=2)
    
    print(f"\nDetailed results written to integration_test_results.json")
    
    # Exit with appropriate code
    exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run_all_tests()