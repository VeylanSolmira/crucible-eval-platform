#!/usr/bin/env python3
"""
Automated test runner for platform demonstrations.

This script runs a curated set of tests to showcase the platform's
capabilities during demos.
"""

import subprocess
import time
import sys
import requests
from typing import List, Tuple

API_BASE_URL = "http://localhost:8000/api"


def print_section(title: str):
    """Print a formatted section header."""
    print()
    print("=" * 60)
    print(f" {title.upper()} ")
    print("=" * 60)
    print()


def check_services() -> bool:
    """Check if all required services are running."""
    print("Checking platform health...", end=" ", flush=True)
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            if health.get("status") == "healthy":
                print("✅ All services healthy")
                return True
        print("❌ Services not healthy")
        return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return False


def run_test_script(script_path: str, args: List[str] = None) -> Tuple[bool, str]:
    """Run a test script and return success status and output."""
    cmd = ["python3", script_path]
    if args:
        cmd.extend(args)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        success = result.returncode == 0
        output = result.stdout + result.stderr
        return success, output
    except subprocess.TimeoutExpired:
        return False, "Test timed out after 5 minutes"
    except Exception as e:
        return False, f"Error running test: {e}"


def run_demo_sequence():
    """Run the demonstration test sequence."""
    print_section("CRUCIBLE PLATFORM DEMO TEST SUITE")
    
    # Check services first
    if not check_services():
        print("\n⚠️  Please ensure all services are running with:")
        print("   docker-compose up -d")
        sys.exit(1)
    
    # Test sequence
    tests = [
        {
            "name": "Core Integration Tests",
            "description": "Tests basic submission, retrieval, and error handling",
            "script": "tests/integration/test_core_flows.py",
            "args": [],
            "critical": True
        },
        {
            "name": "Concurrent Load Test",
            "description": "Tests 10 concurrent evaluations",
            "script": "tests/integration/test_load.py",
            "args": ["10", "20"],
            "critical": False
        },
        {
            "name": "Service Resilience",
            "description": "Tests service restart and failure recovery",
            "script": "tests/integration/test_resilience.py",
            "args": [],
            "critical": False
        }
    ]
    
    results = []
    
    for test in tests:
        print_section(test["name"])
        print(f"Description: {test['description']}")
        print(f"Running: {test['script']}")
        print()
        
        # Run the test
        success, output = run_test_script(test["script"], test["args"])
        results.append({
            "name": test["name"],
            "success": success,
            "critical": test["critical"]
        })
        
        # Show key results
        if success:
            # Extract summary from output
            lines = output.split('\n')
            summary_start = False
            for line in lines:
                if "SUMMARY" in line:
                    summary_start = True
                elif summary_start and line.strip():
                    print(line)
                elif summary_start and "=" in line:
                    break
        else:
            print("❌ Test failed!")
            if test["critical"]:
                print("\n⚠️  Critical test failed. Stopping demo tests.")
                print(f"\nError output:\n{output[-500:]}")  # Last 500 chars
                break
    
    # Final summary
    print_section("DEMO TEST SUMMARY")
    
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed
    
    print(f"Total Tests Run: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print()
    
    for result in results:
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        print(f"{status} - {result['name']}")
    
    if passed == total:
        print("\n🎉 All tests passed! Platform is ready for demo.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please check the logs.")
    
    # Show next steps
    print_section("NEXT STEPS")
    print("1. Review test results in the generated JSON files")
    print("2. Access the platform at http://localhost:3000")
    print("3. Monitor Celery tasks at http://localhost:5555 (Flower)")
    print("4. View API docs at http://localhost:8000/docs")
    print()
    print("For the demo, you can show:")
    print("- Submit code evaluations through the UI")
    print("- Monitor execution in real-time")
    print("- View Celery task processing in Flower")
    print("- Demonstrate load handling with batch submissions")
    print("- Show resilience by restarting services during execution")


def run_quick_check():
    """Run a quick platform check for demos."""
    print_section("QUICK PLATFORM CHECK")
    
    if not check_services():
        return False
    
    # Submit a quick test
    print("Submitting test evaluation...", end=" ", flush=True)
    try:
        response = requests.post(
            f"{API_BASE_URL}/eval",
            json={
                "code": "print('Demo test successful!')",
                "language": "python",
                "engine": "docker",
                "timeout": 10
            },
            timeout=5
        )
        
        if response.status_code == 200:
            eval_id = response.json()["eval_id"]
            print(f"✅ Submitted (ID: {eval_id})")
            
            # Wait for completion
            print("Waiting for completion...", end=" ", flush=True)
            time.sleep(3)
            
            response = requests.get(f"{API_BASE_URL}/eval/{eval_id}", timeout=5)
            if response.status_code == 200:
                status = response.json().get("status")
                if status == "completed":
                    print("✅ Completed successfully")
                    return True
                else:
                    print(f"❌ Status: {status}")
            else:
                print("❌ Cannot retrieve status")
        else:
            print(f"❌ Submission failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        # Quick check mode
        if run_quick_check():
            print("\n✅ Platform is ready for demo!")
            sys.exit(0)
        else:
            print("\n❌ Platform check failed!")
            sys.exit(1)
    else:
        # Full demo test suite
        run_demo_sequence()