#!/usr/bin/env python3
"""
Automated test runner for platform demonstrations.

This script runs a curated set of tests to showcase the platform's
capabilities during demos.

Usage:
    python tests/run_tests.py              # Run all test suites
    python tests/run_tests.py unit         # Run only unit tests
    python tests/run_tests.py security     # Run only security tests
    python tests/run_tests.py unit,security # Run multiple specific suites
    python tests/run_tests.py quick        # Run quick platform check
    python tests/run_tests.py benchmarks   # Run performance benchmarks (long-running)
    
Options:
    -v, --verbose                          # Show detailed test output
    --include-slow                         # Include tests marked as @pytest.mark.slow
    --include-destructive                  # Include tests that stop/restart services
    --dry-run                              # Show which tests would run without executing them

Available test suites: unit, integration, e2e, performance, security, benchmarks
"""

import subprocess
import time
import sys
import requests
from typing import List, Tuple, Dict, Any
import urllib3

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_BASE_URL = "http://localhost/api"


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
        response = requests.get(f"{API_BASE_URL}/health", timeout=5, verify=False)
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


def collect_tests(script_path: str, skip_slow: bool = True) -> Dict[str, Any]:
    """Collect test information without running them."""
    if not (script_path.endswith('.py') and 'test_' in script_path):
        return {"error": "Not a pytest file", "tests": []}
    
    # First, collect ALL tests to see what exists
    all_cmd = ["pytest", script_path, "--collect-only", "-q"]
    try:
        all_result = subprocess.run(all_cmd, capture_output=True, text=True, timeout=10)
        all_output = all_result.stdout + all_result.stderr
        
        all_tests = []
        module_skip_reason = None
        
        for line in all_output.split("\n"):
            if "::" in line and not line.startswith(" "):
                test_name = line.split("::")[-1].strip()
                if test_name and not test_name.startswith("<"):
                    all_tests.append(test_name)
            # Check for module-level skip
            elif "SKIPPED" in line and ".py" in line:
                # Extract skip reason if available
                if ":" in line:
                    module_skip_reason = line.split(":", 1)[1].strip()
            elif "no tests collected" in line and "SKIP" in all_output:
                # Module was skipped before collection
                module_skip_reason = "Module skipped (check skip conditions)"
    except Exception:
        all_tests = []
        module_skip_reason = None
    
    # Now collect with filters applied
    cmd = ["pytest", script_path, "--collect-only", "-q"]
    if skip_slow:
        cmd.extend(["-m", "not slow"])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        output = result.stdout + result.stderr
        
        selected_tests = []
        deselected_count = 0
        
        for line in output.split("\n"):
            if "::" in line and not line.startswith(" "):
                test_name = line.split("::")[-1].strip()
                if test_name and not test_name.startswith("<"):
                    selected_tests.append(test_name)
            elif "deselected" in line:
                import re
                match = re.search(r'(\d+) deselected', line)
                if match:
                    deselected_count = int(match.group(1))
        
        # Figure out which tests were deselected
        deselected_tests = []
        for test in all_tests:
            if test not in selected_tests:
                deselected_tests.append(test)
        
        # If we collected tests but suspect they might be skipped at runtime,
        # do a quick dry-run to check for runtime skips
        runtime_skip_reason = None
        if selected_tests and not module_skip_reason:
            # Run a quick test with -rs to get skip reasons
            skip_cmd = ["pytest", script_path, "-rs", "--tb=no", "--no-header", "-q"]
            try:
                skip_result = subprocess.run(skip_cmd, capture_output=True, text=True, timeout=10)
                skip_output = skip_result.stdout + skip_result.stderr
                
                # Look for skip reasons in the short test summary
                if "SKIPPED" in skip_output and "short test summary info" in skip_output:
                    lines = skip_output.split("\n")
                    in_summary = False
                    skip_reasons = set()
                    
                    for line in lines:
                        if "short test summary info" in line:
                            in_summary = True
                            continue
                        if in_summary and "SKIPPED" in line:
                            # Format: SKIPPED [1] path/to/test.py:line: reason
                            if ":" in line:
                                parts = line.split(":", 2)
                                if len(parts) >= 3:
                                    reason = parts[2].strip()
                                    if reason:
                                        skip_reasons.add(reason)
                    
                    if skip_reasons:
                        # If all tests have the same skip reason, use it
                        if len(skip_reasons) == 1:
                            runtime_skip_reason = skip_reasons.pop()
                        else:
                            runtime_skip_reason = "Multiple skip reasons"
            except Exception:
                # If we can't determine skip reason, that's ok
                pass
        
        return {
            "tests": selected_tests,
            "deselected": deselected_count,
            "deselected_tests": deselected_tests,
            "total": len(selected_tests) + deselected_count,
            "skip_reason": "marked as slow" if skip_slow and deselected_tests else "",
            "module_skip_reason": module_skip_reason,
            "runtime_skip_reason": runtime_skip_reason
        }
    except Exception as e:
        return {"error": str(e), "tests": []}


def run_test_script(script_path: str, args: List[str] = None, skip_slow: bool = True, skip_destructive: bool = True) -> Tuple[bool, str]:
    """Run a test script and return success status and output."""
    # Use pytest for test files, python for scripts
    if script_path.endswith('.py') and 'test_' in script_path:
        cmd = ["pytest", script_path, "-v", "-r", "a"]  # -r a shows all test outcomes
        markers = []
        if skip_slow:
            markers.append("not slow")
        if skip_destructive:
            markers.append("not destructive")
        if markers:
            cmd.extend(["-m", " and ".join(markers)])
    else:
        cmd = ["python3", script_path]
    if args:
        cmd.extend(args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        success = result.returncode == 0
        output = result.stdout + result.stderr
        return success, output
    except subprocess.TimeoutExpired:
        return False, "Test timed out after 5 minutes"
    except Exception as e:
        return False, f"Error running test: {e}"


def parse_pytest_output(output: str) -> Dict[str, Any]:
    """Parse pytest output to extract individual test results."""
    results = {
        "tests": [],
        "summary": "",
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "deselected": 0,
        "skip_reasons": {}
    }
    
    # Look for deselected tests (due to markers)
    for line in output.split("\n"):
        if "deselected by" in line:
            # Extract deselection info: "1 deselected by '-m not slow'"
            import re
            match = re.search(r'(\d+) deselected by "(.+)"', line)
            if match:
                results["deselected"] = int(match.group(1))
                results["skip_reasons"]["marker"] = match.group(2)
    
    # Look for individual test results
    for line in output.split("\n"):
        if " PASSED " in line and "::" in line:
            test_name = line.split("::")[1].split(" PASSED")[0]
            results["tests"].append({"name": test_name.strip(), "status": "PASSED"})
            results["passed"] += 1
        elif " FAILED " in line and "::" in line:
            test_name = line.split("::")[1].split(" FAILED")[0]
            results["tests"].append({"name": test_name.strip(), "status": "FAILED"})
            results["failed"] += 1
        elif " SKIPPED " in line and "::" in line:
            test_name = line.split("::")[1].split(" SKIPPED")[0]
            # Try to extract skip reason
            reason = "unknown"
            if "[" in line and "]" in line:
                reason = line[line.find("[")+1:line.find("]")]
            results["tests"].append({"name": test_name.strip(), "status": "SKIPPED", "reason": reason})
            results["skipped"] += 1
        elif "short test summary" in line.lower():
            # Start capturing summary
            results["summary"] = line
    
    return results


def run_demo_sequence(verbose: bool = False, include_slow: bool = False, include_destructive: bool = False, dry_run: bool = False):
    """Run the demonstration test sequence."""
    print_section("CRUCIBLE PLATFORM TEST SUITE")
    
    if dry_run:
        print("🔍 DRY RUN MODE - Showing which tests would run\n")

    # Check services first
    # TODO: Implement proper health check that validates all services:
    # - API Gateway, Storage Service, Celery Workers, Redis, PostgreSQL, Executors
    # Current check_services() only verifies API gateway responds
    # if not check_services():
    #     print("\n⚠️  Please ensure all services are running with:")
    #     print("   docker compose up -d")
    #     sys.exit(1)

    # Unit Tests
    unit_tests = [
        {
            "name": "API Evaluation Request Validation",
            "description": "Tests Pydantic model validation for evaluation requests",
            "script": "tests/unit/api/test_evaluation_request.py",
            "args": [],
            "critical": False,
        },
        {
            "name": "Celery Retry Configuration",
            "description": "Tests retry logic, exponential backoff, HTTP error classification, and retry strategies",
            "script": "tests/unit/celery/test_retry_config.py",
            "args": [],
            "critical": False,
        },
        {
            "name": "PostgreSQL Operations",
            "description": "Tests PostgreSQL-specific features like JSONB queries",
            "script": "tests/unit/storage/test_postgresql_operations.py",
            "args": [],
            "critical": False,
        },
        {
            "name": "Storage - Memory Backend",
            "description": "Tests in-memory storage backend implementation",
            "script": "tests/unit/storage/test_memory_backend.py",
            "args": [],
            "critical": False,
        },
        {
            "name": "Storage - File Backend",
            "description": "Tests file-based storage backend implementation",
            "script": "tests/unit/storage/test_file_backend.py",
            "args": [],
            "critical": False,
        },
        {
            "name": "Storage - Database Backend",
            "description": "Tests database storage backend implementation",
            "script": "tests/unit/storage/test_database_backend.py",
            "args": [],
            "critical": False,
        },
        {
            "name": "Storage - Flexible Manager",
            "description": "Tests flexible storage manager with caching and fallback",
            "script": "tests/unit/storage/test_flexible_manager.py",
            "args": [],
            "critical": False,
        },
    ]
    
    # Integration Tests
    integration_tests = [
        {
            "name": "Redis State Management",
            "description": "Tests Redis state tracking during evaluation lifecycle",
            "script": "tests/integration/check_redis_state.py",
            "args": [],
            "critical": True,
        },
        {
            "name": "Celery Connection",
            "description": "Tests Celery and Redis connectivity and configuration",
            "script": "tests/integration/test_celery_connection.py",
            "args": [],
            "critical": True,  # Critical - must be able to connect to Celery
        },
        {
            "name": "Celery Direct Tasks",
            "description": "Tests Celery tasks directly without API layer",
            "script": "tests/integration/test_celery_tasks.py",
            "args": [],
            "critical": False,  # Informational - API layer tests cover functionality
        },
        {
            "name": "Celery Task Integration",
            "description": "Tests Celery task chaining and executor allocation",
            "script": "tests/integration/test_celery_integration.py",
            "args": [],
            "critical": True,  # Critical - evaluations can't reach executors without it
        },
        {
            "name": "Fast-Failing Container Logs",
            "description": "Tests Docker event race condition fix for fast-failing containers",
            "script": "tests/integration/test_fast_failing_containers.py",
            "args": [],
            "critical": True,  # Critical - ensures logs are captured from all containers
        },
        {
            "name": "Docker Event Diagnostics",
            "description": "Diagnostic tests for container lifecycle and event handling",
            "script": "tests/integration/test_docker_event_diagnostics.py",
            "args": [],
            "critical": False,  # Informational/diagnostic
        },
        {
            "name": "Executor Import Handling",
            "description": "Tests import error capture and ML library support in executors",
            "script": "tests/integration/test_executor_imports.py",
            "args": [],
            "critical": False,  # Informational - validates executor capabilities
        },
        {
            "name": "Priority Queue API",
            "description": "Tests priority queue functionality via API endpoints",
            "script": "tests/integration/test_priority_queue.py",
            "args": [],
            "critical": False,  # Priority queues are an optimization feature
        },
        {
            "name": "Priority Queue Celery",
            "description": "Tests Celery priority queue direct task submission",
            "script": "tests/integration/test_priority_celery.py",
            "args": [],
            "critical": False,  # Lower-level priority queue testing
        },
        {
            "name": "Core Integration Tests",
            "description": "Tests basic submission, retrieval, and error handling",
            "script": "tests/integration/test_core_flows.py",
            "args": [],
            "critical": True,
        },
        {
            "name": "Service Resilience",
            "description": "Tests service restart and failure recovery (destructive)",
            "script": "tests/integration/test_resilience.py",
            "args": [],
            "critical": False,
            "destructive": True,  # Requires special flag to run
        },
    ]
    
    # E2E Tests
    e2e_tests = [
        # TODO: Add e2e tests when implemented
    ]
    
    # Performance Tests
    performance_tests = [
        {
            "name": "Rate-Aware Load Test",
            "description": "Tests system under load while respecting rate limits",
            "script": "tests/integration/test_load.py",
            "args": ["10", "20", "120"],  # 10 concurrent, 20 total, 2 min timeout
            "critical": False,  # Performance tests are informational
        },
        # TODO: Add more performance tests that verify requirements:
        # - API response time < 100ms
        # - Evaluation submission < 500ms
        # - Handle 10 concurrent evaluations
        # - No memory leaks after 100 evaluations
        # See tests/performance/README.md for guidelines
    ]
    
    # Security Tests
    security_tests = [
        {
            "name": "API Input Validation",
            "description": "Tests that dangerous/malformed inputs are rejected",
            "script": "tests/security/test_input_validation.py",
            "args": [],
            "critical": True,
        },
        # TODO: Add more buildtime security tests:
        # - Container creation security policy verification
        # - API authentication/authorization tests
        # - Security regression tests
        # See tests/security/README.md for test categories
    ]
    
    # Benchmark Tests (Long-running performance measurements)
    benchmark_tests = [
        {
            "name": "Evaluation Throughput Benchmark",
            "description": "Measures evaluations per minute under sustained load (60s test)",
            "script": "tests/benchmarks/test_evaluation_throughput.py",
            "args": [],
            "critical": False,  # Benchmarks are informational
        },
        # TODO: Add more benchmarks:
        # - Storage write throughput
        # - API endpoint latency distribution
        # - Large evaluation handling
        # See tests/benchmarks/README.md for guidelines
    ]
    
    # Combine all test suites
    tests = []
    
    # Add test suites based on what we want to run
    available_suites = {
        "unit": unit_tests,
        "integration": integration_tests,
        "e2e": e2e_tests,
        "performance": performance_tests,
        "security": security_tests,
        "benchmarks": benchmark_tests
    }
    
    # Track which suites we're running for better output
    suites_to_run = []
    
    # Check if specific test suites requested via command line
    if len(sys.argv) > 1 and sys.argv[1] != "quick":
        # Run only specified test suites
        requested_suites = sys.argv[1].split(",")
        for suite_name in requested_suites:
            if suite_name in available_suites:
                suites_to_run.append((suite_name, available_suites[suite_name]))
            else:
                print(f"⚠️  Unknown test suite: {suite_name}")
                print(f"   Available: {', '.join(available_suites.keys())}")
    else:
        # Run all test suites EXCEPT benchmarks (too long for regular runs)
        suites_to_run = [
            ("unit", unit_tests),
            ("integration", integration_tests),
            ("e2e", e2e_tests),
            ("performance", performance_tests),
            ("security", security_tests),
        ]
        # Note: benchmarks excluded from default run due to long duration

    results = []
    
    # Process each suite
    for suite_name, suite_tests in suites_to_run:
        if suite_tests:  # Only show header if suite has tests
            if dry_run:
                print(f"\n{'='*60}")
                print(f" {suite_name.upper()} TESTS")
                print(f"{'='*60}")
            
        for test in suite_tests:
            # Skip destructive tests unless explicitly included
            if test.get("destructive", False) and not include_destructive:
                continue
                
            print_section(test["name"])
            print(f"Description: {test['description']}")
            print(f"Script: {test['script']}")
            
            if dry_run:
                # Just collect test information
                if 'test_' in test["script"]:
                    test_info = collect_tests(test["script"], skip_slow=not include_slow)
                    if test_info.get("error"):
                        print(f"  Error collecting tests: {test_info['error']}")
                    elif test_info.get("module_skip_reason"):
                        print(f"  ⚠️  Module skipped: {test_info['module_skip_reason']}")
                    elif test_info["tests"] or test_info.get("deselected_tests"):
                        if test_info["tests"]:
                            if test_info.get("runtime_skip_reason"):
                                print(f"\n{len(test_info['tests'])} test(s) collected but will be skipped at runtime:")
                                for test_name in test_info["tests"]:
                                    print(f"  ⚠️  {test_name}")
                                print(f"\n  Skip reason: {test_info['runtime_skip_reason']}")
                            else:
                                print(f"\nWould run {len(test_info['tests'])} test(s):")
                                for test_name in test_info["tests"]:
                                    print(f"  • {test_name}")
                        
                        if test_info.get("deselected_tests"):
                            print(f"\nWould skip {len(test_info['deselected_tests'])} test(s):")
                            for test_name in test_info["deselected_tests"]:
                                print(f"  ⚠️  {test_name} ({test_info.get('skip_reason', 'unknown reason')})")
                    else:
                        print("  No tests found")
                else:
                    print("  Would run as Python script (not pytest)")
                continue
            
            print("Running...")
            print()

            # Run the test
            success, output = run_test_script(test["script"], test["args"], skip_slow=not include_slow, skip_destructive=not include_destructive)
            results.append({"name": test["name"], "success": success, "critical": test["critical"]})

            # Show results based on test type and verbosity
            if "pytest" in output or "test_" in test["script"]:
                # This is a pytest run, parse the output
                pytest_results = parse_pytest_output(output)
                
                if pytest_results["tests"]:
                    # Show individual test results
                    for test_result in pytest_results["tests"]:
                        status_icon = "✅" if test_result["status"] == "PASSED" else "❌" if test_result["status"] == "FAILED" else "⚠️"
                        status_line = f"  {status_icon} {test_result['name']}"
                        if test_result["status"] == "SKIPPED" and test_result.get("reason"):
                            status_line += f" [{test_result['reason']}]"
                        print(status_line)
                    
                    # Show summary including deselected tests
                    summary_parts = []
                    if pytest_results["passed"]:
                        summary_parts.append(f"{pytest_results['passed']} passed")
                    if pytest_results["failed"]:
                        summary_parts.append(f"{pytest_results['failed']} failed")
                    if pytest_results["skipped"]:
                        summary_parts.append(f"{pytest_results['skipped']} skipped")
                    if pytest_results["deselected"]:
                        reason = pytest_results["skip_reasons"].get("marker", "")
                        summary_parts.append(f"{pytest_results['deselected']} not run ({reason})")
                    
                    if summary_parts:
                        print(f"\n  Summary: {', '.join(summary_parts)}")
                
                if verbose or not success:
                    print("\n" + "-" * 40 + " Output " + "-" * 40)
                    print(output)
                    print("-" * 88 + "\n")
            else:
                # Non-pytest test, use original logic
                if success:
                    # Extract summary from output
                    lines = output.split("\n")
                    summary_start = False
                    for line in lines:
                        if "SUMMARY" in line:
                            summary_start = True
                        elif summary_start and line.strip():
                            print(line)
                        elif summary_start and "=" in line:
                            break
                    
                    if verbose:
                        print("\n" + "-" * 40 + " Output " + "-" * 40)
                        print(output)
                        print("-" * 88 + "\n")
                else:
                    print("❌ Test failed!")
                    if test["critical"]:
                        print("\n⚠️  Critical test failed. Stopping demo tests.")
                        print(f"\nError output:\n{output[-500:]}")  # Last 500 chars
                        break
                    elif verbose:
                        print(f"\nFull output:\n{output}")

    # Final summary
    print_section("TEST SUMMARY")

    if dry_run:
        print(f"DRY RUN COMPLETE")
        print(f"\nTest Categories Selected:")
        
        # Count tests in each suite that was selected
        total_tests = 0
        for suite_name, suite_tests in suites_to_run:
            if suite_tests:
                count = len(suite_tests)
                total_tests += count
                print(f"  ✓ {suite_name.title()} Tests: {count} suite(s)")
        
        print(f"\nTotal test suites that would run: {total_tests}")
        if not include_slow:
            print(f"\nNote: Tests marked as @pytest.mark.slow would be skipped")
            print(f"      Add --include-slow to include them")
    else:
        total = len(results)
        passed = sum(1 for r in results if r["success"])
        failed = total - passed

        print(f"Test Categories:")
        print(f"  Unit Tests:        {len(unit_tests)}")
        print(f"  Integration Tests: {len(integration_tests)}")
        print(f"  E2E Tests:         {len(e2e_tests)}")
        print(f"  Performance Tests: {len(performance_tests)}")
        print(f"  Security Tests:    {len(security_tests)}")
        print(f"  Benchmarks:        {len(benchmark_tests)} (run separately)")
        print()
        print(f"Total Tests Run: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        
        if not include_slow:
            print(f"\nNote: Tests marked as @pytest.mark.slow were skipped")
            print(f"      Run with --include-slow to include them")
        if not include_destructive:
            print(f"\nNote: Destructive tests (that stop/restart services) were skipped")
            print(f"      Run with --include-destructive to include them")
        print()

        for result in results:
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            print(f"{status} - {result['name']}")

    if not dry_run:
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

    # if not check_services():
    #     return False

    # Submit a quick test
    print("Submitting test evaluation...", end=" ", flush=True)
    try:
        response = requests.post(
            f"{API_BASE_URL}/eval",
            json={
                "code": "print('Demo test successful!')",
                "language": "python",
                "engine": "docker",
                "timeout": 10,
            },
            timeout=5,
            verify=False,
        )

        if response.status_code == 200:
            eval_id = response.json()["eval_id"]
            print(f"✅ Submitted (ID: {eval_id})")

            # Wait for completion
            print("Waiting for completion...", end=" ", flush=True)
            time.sleep(3)

            response = requests.get(f"{API_BASE_URL}/eval/{eval_id}", timeout=5, verify=False)
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
    # Check for flags
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    include_slow = "--include-slow" in sys.argv
    include_destructive = "--include-destructive" in sys.argv
    dry_run = "--dry-run" in sys.argv
    
    # Remove flags from args
    sys.argv = [arg for arg in sys.argv if arg not in ["-v", "--verbose", "--include-slow", "--include-destructive", "--dry-run"]]
    
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
        run_demo_sequence(verbose=verbose, include_slow=include_slow, include_destructive=include_destructive, dry_run=dry_run)
