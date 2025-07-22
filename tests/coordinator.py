#!/usr/bin/env python3
"""
Test coordinator that runs inside the Kubernetes cluster.

This script:
1. Discovers which tests to run
2. Creates parallel jobs for each test suite
3. Monitors job execution
4. Aggregates results

This is executed by the coordinator job created by test_orchestrator.py
"""

import subprocess
import sys
import os
import json
import time
import argparse
import re
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed


class TestCoordinator:
    """Coordinates parallel test execution inside the cluster."""
    
    def __init__(self, timestamp: str):
        self.timestamp = timestamp
        self.namespace = os.environ.get("K8S_NAMESPACE", "crucible")
        self.test_image = os.environ.get("TEST_IMAGE", "crucible-test-runner:latest")
        self.test_jobs = []
        self.verbose = False
        
        # Check if we're in production mode
        self.production_mode = os.environ.get("PRODUCTION_MODE", "false").lower() == "true"
        self.image_pull_policy = "Always" if self.production_mode else "Never"
        
    def discover_test_suites(self, requested_suites: List[str], test_files: List[str] = None) -> List[Dict[str, str]]:
        """Discover which test suites to run or specific test files."""
        
        # Define available test suites and their paths
        all_suites = {
            "unit": {
                "path": "tests/unit",
                "description": "Unit tests",
                "parallel_safe": True
            },
            "integration": {
                "path": "tests/integration", 
                "description": "Integration tests",
                "parallel_safe": True
            },
            "e2e": {
                "path": "tests/e2e",
                "description": "End-to-end tests",
                "parallel_safe": False  # May need sequential execution
            },
            "performance": {
                "path": "tests/performance",
                "description": "Performance tests",
                "parallel_safe": False  # Resource intensive
            },
            "security": {
                "path": "tests/security",
                "description": "Security tests",
                "parallel_safe": True
            }
        }
        
        # Determine which suites to run
        if "all" in requested_suites or not requested_suites:
            suites_to_run = list(all_suites.keys())
        else:
            suites_to_run = [s for s in requested_suites if s in all_suites]
        
        # If specific test files requested, handle them differently
        if test_files:
            suite_info = []
            for test_file in test_files:
                # Check if it's a path without "tests/" prefix (e.g., unit/storage/test_file.py)
                test_path = f"/app/tests/{test_file}"
                if os.path.exists(test_path):
                    # Extract the suite name from the path
                    path_parts = test_file.split('/')
                    suite_name = path_parts[0] if path_parts else "unknown"
                    
                    # Find the suite's parallel_safe setting
                    parallel_safe = all_suites.get(suite_name, {}).get("parallel_safe", True)
                    
                    # Create a shorter name for the test file
                    file_name = os.path.basename(test_file).replace('.py', '')
                    # Use just the filename for the suite name to keep it short
                    suite_info.append({
                        "name": file_name,
                        "path": test_path,
                        "description": f"Test file: {test_file}",
                        "parallel_safe": parallel_safe,
                        "test_count": 1  # Will be counted properly later
                    })
                else:
                    print(f"⚠️  Test file not found: {test_file} (looked at {test_path})")
            return suite_info
        
        # Build suite info for full suites
        suite_info = []
        for suite_name in suites_to_run:
            suite = all_suites[suite_name]
            
            # Check if test directory exists
            if os.path.exists(f"/app/{suite['path']}"):
                # Count tests in suite
                test_count = 0
                for root, dirs, files in os.walk(f"/app/{suite['path']}"):
                    test_count += sum(1 for f in files if f.startswith("test_") and f.endswith(".py"))
                
                if test_count > 0:
                    suite_info.append({
                        "name": suite_name,
                        "path": suite["path"],
                        "description": suite["description"],
                        "test_count": test_count,
                        "parallel_safe": suite["parallel_safe"]
                    })
                    print(f"  ✓ {suite_name}: {test_count} test files found")
                else:
                    print(f"  ⚠ {suite_name}: No tests found")
            else:
                print(f"  ⚠ {suite_name}: Directory not found")
        
        return suite_info
    
    def create_test_job(self, 
                       suite: Dict[str, str],
                       job_number: int,
                       pytest_args: List[str]) -> Dict:
        """Create a job manifest for a test suite."""
        
        job_name = f"{suite['name']}-tests-{self.timestamp}-{job_number:02d}".replace("_", "-")
        
        # Build pytest command
        pytest_cmd = [
            "python", "-m", "pytest",
            suite["path"],
            "-v",
            "--tb=short",
            "--junit-xml=/tmp/junit.xml"
        ] + pytest_args
        
        job_manifest = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": job_name,
                "namespace": self.namespace,
                "labels": {
                    "app": "test-runner",
                    "test-suite": suite["name"].replace("_", "-"),
                    "test-run": self.timestamp,
                    "coordinator": f"coordinator-{self.timestamp}"
                }
            },
            "spec": {
                "backoffLimit": 0,
                "activeDeadlineSeconds": 1800,  # 30 minutes per suite
                "ttlSecondsAfterFinished": 86400,  # Clean up after 24 hours
                "template": {
                    "spec": {
                        "serviceAccountName": "test-runner",
                        "priorityClassName": "test-runner-priority",
                        "containers": [{
                            "name": "test-runner",
                            "image": self.test_image,
                            "imagePullPolicy": self.image_pull_policy,
                            "env": [
                                {"name": "IN_CLUSTER_TESTS", "value": "true"},
                                {"name": "K8S_NAMESPACE", "value": self.namespace},
                                {"name": "TEST_DATABASE_URL", "value": f"postgresql://crucible:changeme@postgres.{self.namespace}.svc.cluster.local:5432/test_crucible"},
                                {"name": "REDIS_URL", "value": f"redis://redis.{self.namespace}.svc.cluster.local:6379/0"},
                                {"name": "CELERY_BROKER_URL", "value": f"redis://celery-redis.{self.namespace}.svc.cluster.local:6379/0"},
                                {"name": "API_URL", "value": f"http://api-service.{self.namespace}.svc.cluster.local:8080/api"},
                            ],
                            "command": pytest_cmd,
                            "resources": {
                                "requests": {
                                    "memory": "512Mi",
                                    "cpu": "250m"
                                },
                                "limits": {
                                    "memory": "1Gi",
                                    "cpu": "1"
                                }
                            }
                        }],
                        "restartPolicy": "Never"
                    }
                }
            }
        }
        
        return job_manifest
    
    def submit_job(self, job_manifest: Dict) -> Tuple[str, bool]:
        """Submit a test job and return (job_name, success)."""
        job_name = job_manifest["metadata"]["name"]
        
        
        result = subprocess.run(
            ["kubectl", "apply", "-f", "-"],
            input=json.dumps(job_manifest),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"  ✓ Submitted: {job_name}")
            return job_name, True
        else:
            print(f"  ✗ Failed to submit: {job_name}")
            print(f"    Error: {result.stderr}")
            return job_name, False
    
    def monitor_job(self, job_name: str) -> Dict[str, any]:
        """Monitor a job until completion and return results."""
        print(f"\n📊 Monitoring: {job_name}")
        
        if self.verbose:
            print("  Verbose mode: Will show full output on failure")
        
        start_time = time.time()
        
        # Wait for job to complete
        while True:
            result = subprocess.run(
                ["kubectl", "get", "job", job_name, "-n", self.namespace, "-o", "json"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return {
                    "job_name": job_name,
                    "status": "error",
                    "error": "Failed to get job status",
                    "duration": time.time() - start_time
                }
            
            job_data = json.loads(result.stdout)
            status = job_data.get("status", {})
            
            if status.get("succeeded", 0) > 0 or status.get("failed", 0) > 0:
                # Get logs regardless of job status
                log_result = subprocess.run(
                    ["kubectl", "logs", f"job/{job_name}", "-n", self.namespace],
                    capture_output=True,
                    text=True
                )
                
                # Parse test results from pytest summary line
                import re
                passed = failed = skipped = 0
                found_results = False
                
                for line in reversed(log_result.stdout.split('\n')):
                    if '=====' in line and (' passed' in line or ' failed' in line or ' skipped' in line):
                        # This is likely the summary line
                        # Parse all test counts in one pass
                        counts = {'passed': 0, 'failed': 0, 'skipped': 0}
                        for match in re.finditer(r'(\d+) (passed|failed|skipped)', line):
                            count, status = match.groups()
                            counts[status] = int(count)
                        
                        passed = counts['passed']
                        failed = counts['failed'] 
                        skipped = counts['skipped']
                        found_results = any(counts.values())
                        break
                
                if not found_results:
                    # If job failed and no results, get tail of logs for error
                    if status.get("failed", 0) > 0:
                        return {
                            "job_name": job_name,
                            "status": "failed",
                            "error": log_result.stdout if self.verbose else log_result.stdout[-2000:],
                            "duration": time.time() - start_time
                        }
                    else:
                        return {
                            "job_name": job_name,
                            "status": "error",
                            "error": "No TEST_RESULTS_JSON found in output",
                            "duration": time.time() - start_time
                        }
                
                return {
                    "job_name": job_name,
                    "status": "succeeded",
                    "passed": passed,
                    "failed": failed,
                    "skipped": skipped,
                    "duration": time.time() - start_time
                }
                
            elif False:  # This block is now unreachable
                # Get logs for failure details
                log_result = subprocess.run(
                    ["kubectl", "logs", f"job/{job_name}", "-n", self.namespace, "--tail=50"],
                    capture_output=True,
                    text=True
                )
                
                return {
                    "job_name": job_name,
                    "status": "failed",
                    "error": log_result.stdout[-500:],  # Last 500 chars
                    "duration": time.time() - start_time
                }
            
            # Still running
            time.sleep(5)
    
    def run_parallel(self, suites: List[Dict], pytest_args: List[str]) -> Dict[str, List]:
        """Run test suites in parallel."""
        print("\n🚀 Running tests in PARALLEL mode")
        
        results = {"succeeded": [], "failed": []}
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all jobs
            future_to_job = {}
            
            for i, suite in enumerate(suites):
                if suite["parallel_safe"]:
                    job_manifest = self.create_test_job(suite, i, pytest_args)
                    job_name, submitted = self.submit_job(job_manifest)
                    
                    if submitted:
                        future = executor.submit(self.monitor_job, job_name)
                        future_to_job[future] = suite["name"]
                        self.test_jobs.append(job_name)
            
            # Monitor completion
            for future in as_completed(future_to_job):
                suite_name = future_to_job[future]
                result = future.result()
                
                if result["status"] == "succeeded":
                    results["succeeded"].append(result)
                    print(f"✅ {suite_name}: {result['passed']} passed, "
                          f"{result['failed']} failed, {result['skipped']} skipped "
                          f"({result['duration']:.1f}s)")
                else:
                    results["failed"].append(result)
                    print(f"❌ {suite_name}: {result['status']} ({result['duration']:.1f}s)")
        
        # Run non-parallel-safe tests sequentially
        for i, suite in enumerate(suites):
            if not suite["parallel_safe"]:
                print(f"\n⚠️  Running {suite['name']} sequentially (not parallel safe)")
                job_manifest = self.create_test_job(suite, i + 100, pytest_args)
                job_name, submitted = self.submit_job(job_manifest)
                
                if submitted:
                    self.test_jobs.append(job_name)
                    result = self.monitor_job(job_name)
                    
                    if result["status"] == "succeeded":
                        results["succeeded"].append(result)
                    else:
                        results["failed"].append(result)
        
        return results
    
    def run_sequential(self, suites: List[Dict], pytest_args: List[str]) -> Dict[str, List]:
        """Run test suites sequentially."""
        print("\n🚶 Running tests in SEQUENTIAL mode")
        
        results = {"succeeded": [], "failed": []}
        
        for i, suite in enumerate(suites):
            print(f"\n▶️  Running {suite['name']} ({suite['test_count']} test files)")
            
            job_manifest = self.create_test_job(suite, i, pytest_args)
            job_name, submitted = self.submit_job(job_manifest)
            
            if submitted:
                self.test_jobs.append(job_name)
                result = self.monitor_job(job_name)
                
                if result["status"] == "succeeded":
                    results["succeeded"].append(result)
                    print(f"✅ Completed: {result['passed']} passed, "
                          f"{result['failed']} failed, {result['skipped']} skipped")
                else:
                    results["failed"].append(result)
                    print(f"❌ Failed: {result.get('error', 'Unknown error')}")
        
        return results
    
    def cleanup_jobs(self, preserve_failed=True, preserve_all=False):
        """Clean up all test jobs."""
        print("\n🧹 Cleaning up test jobs...")
        print("   (Preserving all test jobs for debugging)")
        print("   To clean up manually:")
        print(f"   kubectl delete jobs -n {self.namespace} -l test-run={self.timestamp}")
        return
        
        for job_name in self.test_jobs:
            if preserve_failed:
                # Get job details to check if we should preserve it
                result = subprocess.run(
                    ["kubectl", "get", "job", job_name, "-n", self.namespace, "-o", "json"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    job_data = json.loads(result.stdout)
                    status = job_data.get("status", {})
                    
                    # Preserve if job failed
                    if status.get("failed", 0) > 0:
                        print(f"   ⚠️  Preserving failed job: {job_name}")
                        continue
                    
                    # Also check if job had 0 tests (could indicate path issues)
                    if status.get("succeeded", 0) > 0:
                        # Get logs to check test count
                        log_result = subprocess.run(
                            ["kubectl", "logs", f"job/{job_name}", "-n", self.namespace, "--tail=20"],
                            capture_output=True,
                            text=True
                        )
                        if "0 passed" in log_result.stdout or "collected 0 items" in log_result.stdout:
                            print(f"   ⚠️  Preserving job with no tests found: {job_name}")
                            continue
            
            # Delete the job
            subprocess.run(
                ["kubectl", "delete", "job", job_name, "-n", self.namespace, "--wait=false"],
                capture_output=True
            )
            print(f"   ✓ Cleaned up: {job_name}")
    
    def print_summary(self, results: Dict[str, List]):
        """Print final test summary."""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        total_passed = sum(r.get("passed", 0) for r in results["succeeded"])
        total_failed = sum(r.get("failed", 0) for r in results["succeeded"])
        total_skipped = sum(r.get("skipped", 0) for r in results["succeeded"])
        
        print(f"\nTest Suites:")
        print(f"  Succeeded: {len(results['succeeded'])}")
        print(f"  Failed: {len(results['failed'])}")
        
        print(f"\nTest Cases:")
        print(f"  Passed: {total_passed}")
        print(f"  Failed: {total_failed}")
        print(f"  Skipped: {total_skipped}")
        
        if results["failed"]:
            print("\n❌ FAILED SUITES:")
            for result in results["failed"]:
                error = result.get('error', 'Unknown error')
                if self.verbose:
                    print(f"  - {result['job_name']}:")
                    print(f"    {error}")
                else:
                    print(f"  - {result['job_name']}: {error[:500]}...")
        
        return len(results["failed"]) == 0
    
    def run(self,
            requested_suites: List[str],
            parallel: bool = False,
            include_slow: bool = False,
            include_destructive: bool = False,
            test_files: List[str] = None,
            verbose: bool = False) -> int:
        """Main coordinator entry point."""
        
        self.verbose = verbose
        
        print("="*80)
        print("TEST COORDINATOR")
        print("="*80)
        print(f"\nRunning inside cluster in namespace: {self.namespace}")
        print(f"Test image: {self.test_image}")
        
        # Build pytest args
        pytest_args = []
        if not include_slow:
            pytest_args.extend(["-m", "not slow"])
        if not include_destructive:
            pytest_args.extend(["-m", "not destructive"]) if pytest_args else pytest_args.extend(["-m", "not destructive"])
        
        # Discover test suites or specific test files
        if test_files:
            print(f"\n📦 Discovering test files: {test_files}")
        else:
            print("\n📦 Discovering test suites...")
        suites = self.discover_test_suites(requested_suites, test_files)
        
        if not suites:
            print("\n⚠️  No test suites found!")
            return 1
        
        print(f"\nFound {len(suites)} test suites to run")
        
        try:
            # Run tests
            if parallel:
                results = self.run_parallel(suites, pytest_args)
            else:
                results = self.run_sequential(suites, pytest_args)
            
            # Print summary
            all_passed = self.print_summary(results)
            
            return 0 if all_passed else 1
            
        finally:
            self.cleanup_jobs()


def main():
    """Parse arguments and run coordinator."""
    parser = argparse.ArgumentParser(description="Test coordinator")
    parser.add_argument("--timestamp", required=True, help="Test run timestamp")
    parser.add_argument("--suites", nargs="+", default=["all"], help="Test suites to run")
    parser.add_argument("--test-files", nargs="+", help="Specific test files to run")
    parser.add_argument("--parallel", action="store_true", help="Run in parallel")
    parser.add_argument("--sequential", action="store_true", help="Run sequentially")
    parser.add_argument("--include-slow", action="store_true", help="Include slow tests")
    parser.add_argument("--include-destructive", action="store_true", help="Include destructive tests")
    parser.add_argument("--verbose", action="store_true", help="Show full output and logs (no truncation)")
    
    args = parser.parse_args()
    
    coordinator = TestCoordinator(args.timestamp)
    exit_code = coordinator.run(
        requested_suites=args.suites,
        parallel=args.parallel,
        include_slow=args.include_slow,
        include_destructive=args.include_destructive,
        test_files=args.test_files,
        verbose=args.verbose
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()