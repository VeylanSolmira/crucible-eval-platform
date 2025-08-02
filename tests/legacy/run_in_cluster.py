#!/usr/bin/env python3
"""
Run tests inside the Kubernetes cluster as Jobs.

This is the next step after smoke tests pass. It:
1. Builds/uses test runner image
2. Submits tests as Kubernetes Jobs
3. Streams logs back to console
4. Reports results

Usage:
    python tests/run_in_cluster.py              # Run all non-destructive tests
    python tests/run_in_cluster.py integration  # Run specific suite
    python tests/run_in_cluster.py --destructive  # Include destructive tests
"""

import subprocess
import sys
import os
import json
import time
import yaml
from datetime import datetime
from typing import Dict, List, Optional


class ClusterTestRunner:
    """Runs tests inside Kubernetes cluster as Jobs."""
    
    def __init__(self):
        self.namespace = os.environ.get("K8S_NAMESPACE", "crucible")
        self.test_image = os.environ.get(
            "TEST_RUNNER_IMAGE",
            "crucible-test-runner:latest"  # Would be ECR URL in real setup
        )
        self.timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
    def create_test_job(self, 
                       test_suite: str,
                       job_name: str,
                       test_args: List[str],
                       namespace: Optional[str] = None) -> Dict:
        """Create a Kubernetes Job manifest for running tests."""
        namespace = namespace or self.namespace
        
        # Build pytest command
        pytest_cmd = ["python", "-m", "pytest", "-v", "-s", "--tb=short"]
        
        # Add test path
        if test_suite == "all":
            pytest_cmd.append("tests/")
        else:
            pytest_cmd.append(f"tests/{test_suite}/")
        
        # Add any additional arguments
        pytest_cmd.extend(test_args)
        
        # Job manifest
        job_manifest = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": job_name,
                "namespace": namespace,
                "labels": {
                    "app": "test-runner",
                    "test-suite": test_suite,
                    "test-run": self.timestamp
                }
            },
            "spec": {
                "backoffLimit": 0,  # Don't retry test failures
                "activeDeadlineSeconds": 1800,  # 30 minute timeout
                "template": {
                    "spec": {
                        "serviceAccountName": "test-runner",
                        "containers": [{
                            "name": "test-runner",
                            "image": self.test_image,
                            "imagePullPolicy": "Always",
                            "env": [
                                {"name": "IN_CLUSTER_TESTS", "value": "true"},
                                {"name": "PYTHONUNBUFFERED", "value": "1"},
                                {"name": "K8S_NAMESPACE", "value": namespace},
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
    
    def submit_test_job(self, job_manifest: Dict) -> bool:
        """Submit a test job to Kubernetes."""
        job_name = job_manifest["metadata"]["name"]
        
        # Apply the job
        print(f"\n🚀 Submitting test job: {job_name}")
        
        result = subprocess.run(
            ["kubectl", "apply", "-f", "-"],
            input=json.dumps(job_manifest),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ Failed to create job: {result.stderr}")
            return False
            
        print(f"✅ Job created successfully")
        return True
    
    def stream_job_logs(self, job_name: str, namespace: str) -> int:
        """Stream logs from a running job."""
        print(f"\n📋 Streaming logs from {job_name}...")
        print("-" * 80)
        
        # Wait for pod to be created
        for _ in range(30):
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", namespace,
                 "-l", f"job-name={job_name}", "-o", "json"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                pods = json.loads(result.stdout)
                if pods["items"]:
                    break
            
            time.sleep(1)
        else:
            print("❌ Pod not created within 30 seconds")
            return 1
        
        # Stream logs
        log_process = subprocess.Popen(
            ["kubectl", "logs", "-f", f"job/{job_name}", "-n", namespace],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Stream output line by line
        for line in log_process.stdout:
            print(line, end='')
        
        log_process.wait()
        
        # Get job status
        result = subprocess.run(
            ["kubectl", "get", "job", job_name, "-n", namespace, "-o", "json"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            job_data = json.loads(result.stdout)
            succeeded = job_data["status"].get("succeeded", 0)
            failed = job_data["status"].get("failed", 0)
            
            print("-" * 80)
            if succeeded > 0:
                print(f"✅ Tests completed successfully")
                return 0
            else:
                print(f"❌ Tests failed")
                return 1
        
        return 1
    
    def cleanup_job(self, job_name: str, namespace: str):
        """Clean up completed job."""
        print(f"\n🧹 Cleaning up job {job_name}...")
        subprocess.run(
            ["kubectl", "delete", "job", job_name, "-n", namespace, "--wait=false"],
            capture_output=True
        )
    
    def ensure_test_service_account(self):
        """Ensure test runner service account exists."""
        sa_manifest = {
            "apiVersion": "v1",
            "kind": "ServiceAccount",
            "metadata": {
                "name": "test-runner",
                "namespace": self.namespace
            }
        }
        
        # Try to create, ignore if already exists
        subprocess.run(
            ["kubectl", "apply", "-f", "-"],
            input=json.dumps(sa_manifest),
            capture_output=True
        )
    
    def run_test_suite(self, 
                      test_suite: str = "all",
                      include_destructive: bool = False) -> int:
        """Run a test suite inside the cluster."""
        
        # Ensure service account exists
        self.ensure_test_service_account()
        
        # Determine test arguments
        test_args = []
        if not include_destructive:
            test_args.extend(["-m", "not destructive"])
        
        # For specific test suites
        job_name = f"{test_suite}-tests-{self.timestamp}"
        
        # Create job manifest
        job_manifest = self.create_test_job(
            test_suite=test_suite,
            job_name=job_name,
            test_args=test_args,
            namespace=self.namespace
        )
        
        # Submit job
        if not self.submit_test_job(job_manifest):
            return 1
        
        # Stream logs and get result
        try:
            exit_code = self.stream_job_logs(job_name, self.namespace)
            return exit_code
        finally:
            # Always cleanup
            self.cleanup_job(job_name, self.namespace)


def main():
    """Main entry point."""
    print("=" * 80)
    print("Kubernetes In-Cluster Test Runner")
    print("=" * 80)
    
    # Parse arguments
    test_suite = "all"
    include_destructive = False
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--destructive":
            include_destructive = True
        else:
            test_suite = sys.argv[1]
    
    if "--destructive" in sys.argv:
        include_destructive = True
    
    # Create runner
    runner = ClusterTestRunner()
    
    print(f"\nConfiguration:")
    print(f"  Namespace: {runner.namespace}")
    print(f"  Test Image: {runner.test_image}")
    print(f"  Test Suite: {test_suite}")
    print(f"  Include Destructive: {include_destructive}")
    
    # Run tests
    exit_code = runner.run_test_suite(test_suite, include_destructive)
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()