#!/usr/bin/env python3
"""
Analyze test failures from parallel runs to understand the root cause.
"""

import subprocess
import json
import sys
import re
from collections import defaultdict
from datetime import datetime

def get_test_logs(namespace="dev", test_run_label=None):
    """Get logs from all test jobs in a test run."""
    if not test_run_label:
        # Find the most recent test run
        result = subprocess.run(
            ["kubectl", "get", "jobs", "-n", namespace, 
             "-l", "app=test-runner", "-o", "json"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            jobs = json.loads(result.stdout).get("items", [])
            if jobs:
                # Get the most recent test-run label
                test_runs = set()
                for job in jobs:
                    labels = job["metadata"]["labels"]
                    if "test-run" in labels:
                        test_runs.add(labels["test-run"])
                if test_runs:
                    test_run_label = sorted(test_runs)[-1]
                    print(f"Using most recent test run: {test_run_label}")
    
    if not test_run_label:
        print("No test run found")
        return {}
    
    # Get all jobs from this test run
    result = subprocess.run(
        ["kubectl", "get", "jobs", "-n", namespace,
         "-l", f"test-run={test_run_label}", "-o", "json"],
        capture_output=True, text=True
    )
    
    logs = {}
    if result.returncode == 0:
        jobs = json.loads(result.stdout).get("items", [])
        for job in jobs:
            job_name = job["metadata"]["name"]
            suite_name = job["metadata"]["labels"].get("test-suite", "unknown")
            
            # Get logs
            log_result = subprocess.run(
                ["kubectl", "logs", f"job/{job_name}", "-n", namespace],
                capture_output=True, text=True
            )
            
            if log_result.returncode == 0:
                logs[suite_name] = log_result.stdout
                
    return logs

def analyze_pytest_output(log_text):
    """Parse pytest output to find test results and failures."""
    results = {
        "passed": [],
        "failed": [],
        "error": [],
        "timeout": [],
        "summary": {}
    }
    
    # Parse test results
    for line in log_text.split('\n'):
        # Look for test results
        if "PASSED" in line and "::" in line:
            test_name = line.split()[0]
            results["passed"].append(test_name)
        elif "FAILED" in line and "::" in line:
            test_name = line.split()[0]
            results["failed"].append(test_name)
        elif "ERROR" in line and "::" in line:
            test_name = line.split()[0]
            results["error"].append(test_name)
            
        # Look for summary line
        if "failed" in line and "passed" in line and "=" in line:
            # Parse summary like "1 failed, 2 passed, 3 skipped in 10.5s"
            match = re.search(r'(\d+) failed.*?(\d+) passed', line)
            if match:
                results["summary"]["failed"] = int(match.group(1))
                results["summary"]["passed"] = int(match.group(2))
                
    return results

def analyze_evaluation_failures(log_text):
    """Extract evaluation-specific failure patterns."""
    eval_failures = defaultdict(dict)
    
    lines = log_text.split('\n')
    for i, line in enumerate(lines):
        # Look for evaluation submissions
        if "[EVAL_SUBMIT]" in line:
            match = re.search(r'eval_id=(\S+)', line)
            if match:
                eval_id = match.group(1)
                eval_failures[eval_id]["submitted"] = True
                
        # Look for evaluation status updates
        if "provisioning" in line and "s]" in line:
            # Extract eval ID from status line like "[12.3s] eval_id: provisioning"
            match = re.search(r'\[[\d.]+s\] (\S+): (\w+)', line)
            if match:
                eval_id = match.group(1)
                status = match.group(2)
                eval_failures[eval_id]["last_status"] = status
                
                # Track how long it was provisioning
                time_match = re.search(r'\[([\d.]+)s\]', line)
                if time_match:
                    eval_failures[eval_id]["last_time"] = float(time_match.group(1))
                    
        # Look for "Evaluations without pods"
        if "Evaluations without pods" in line:
            # Check next few lines for eval IDs
            for j in range(i+1, min(i+5, len(lines))):
                if lines[j].strip().startswith("- "):
                    eval_id = lines[j].strip()[2:]
                    eval_failures[eval_id]["no_pod"] = True
                    
    return eval_failures

def compare_test_runs():
    """Compare parallel vs individual test runs."""
    print("=== TEST FAILURE ANALYSIS ===\n")
    
    # Get logs from the most recent test run
    logs = get_test_logs()
    
    if not logs:
        print("No test logs found")
        return
        
    # Analyze each test suite
    for suite_name, log_text in logs.items():
        print(f"\n### {suite_name.upper()} TESTS ###")
        
        # Parse pytest results
        results = analyze_pytest_output(log_text)
        
        print(f"Passed: {len(results['passed'])}")
        print(f"Failed: {len(results['failed'])}")
        print(f"Errors: {len(results['error'])}")
        
        if results["failed"]:
            print("\nFailed tests:")
            for test in results["failed"]:
                print(f"  - {test}")
                
        # Analyze evaluation failures
        eval_failures = analyze_evaluation_failures(log_text)
        
        provisioning_timeouts = []
        no_pod_evals = []
        
        for eval_id, info in eval_failures.items():
            if info.get("no_pod"):
                no_pod_evals.append(eval_id)
            if info.get("last_status") == "provisioning" and info.get("last_time", 0) > 30:
                provisioning_timeouts.append((eval_id, info["last_time"]))
                
        if provisioning_timeouts:
            print(f"\nEvaluations stuck in provisioning (>30s):")
            for eval_id, duration in sorted(provisioning_timeouts, key=lambda x: x[1], reverse=True):
                print(f"  - {eval_id}: {duration:.1f}s")
                
        if no_pod_evals:
            print(f"\nEvaluations without pods:")
            for eval_id in no_pod_evals:
                print(f"  - {eval_id}")
                
    # Check dispatcher logs for errors
    print("\n### CHECKING DISPATCHER ###")
    result = subprocess.run(
        ["kubectl", "logs", "-n", "dev", "deployment/dispatcher", "--tail=500"],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        dispatcher_errors = []
        for line in result.stdout.split('\n'):
            if "ERROR" in line or "Failed to create job" in line:
                dispatcher_errors.append(line)
                
        if dispatcher_errors:
            print(f"\nFound {len(dispatcher_errors)} dispatcher errors:")
            for error in dispatcher_errors[-5:]:  # Show last 5
                print(f"  {error}")
        else:
            print("No dispatcher errors found")
            
    # Check for ResourceQuota issues
    print("\n### CHECKING RESOURCE QUOTAS ###")
    result = subprocess.run(
        ["kubectl", "describe", "resourcequota", "-n", "dev"],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        print(result.stdout)

if __name__ == "__main__":
    compare_test_runs()