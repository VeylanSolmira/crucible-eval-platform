#!/usr/bin/env python3
"""
Main test orchestrator for Kubernetes testing.

This is the single entry point that:
1. Runs smoke tests locally
2. Builds and pushes test image
3. Submits coordinator job to cluster
4. Monitors results

Usage:
    python test_orchestrator.py                    # Run all tests
    python test_orchestrator.py unit integration   # Run specific suites
    python test_orchestrator.py --skip-build       # Skip image build
    python test_orchestrator.py --parallel         # Run tests in parallel
"""

import subprocess
import sys
import os
import json
import time
import argparse
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class TestOrchestrator:
    """Orchestrates the entire test pipeline."""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.namespace = os.environ.get("K8S_NAMESPACE", "crucible")
        
        # Check if we're in production mode
        self.production_mode = os.environ.get("PRODUCTION_MODE", "false").lower() == "true"
        
        if self.production_mode:
            # Production mode: use registry
            print("🏭 Running in PRODUCTION mode - using container registry")
            
            # Docker Hub configuration
            self.docker_hub_user = os.environ.get("DOCKER_HUB_USER")
            
            # Registry precedence: ECR > Docker Hub > Error
            if os.environ.get("ECR_REGISTRY"):
                self.registry = os.environ.get("ECR_REGISTRY")
                print(f"🔍 Debug - Found ECR_REGISTRY in environment: {self.registry}")
                # Use the existing crucible-platform repository
                self.test_image = f"{self.registry}/crucible-platform:test-runner-latest"
            elif self.docker_hub_user:
                self.registry = "docker.io"  # Docker Hub
                self.test_image = f"{self.docker_hub_user}/crucible-test-runner:latest"
            else:
                raise ValueError(
                    "No registry configured. Please set either ECR_REGISTRY or DOCKER_HUB_USER in your .env file"
                )
            self.image_pull_policy = "Always"
        else:
            # Local mode: no registry needed
            print("🏠 Running in LOCAL mode - using local images only")
            self.registry = ""
            self.test_image = "crucible-platform/test-runner:latest"
            self.image_pull_policy = "Never"
            
        self.coordinator_job_name = f"test-coordinator-{self.timestamp}"
        
    def run_smoke_tests(self) -> bool:
        """Step 1: Run smoke tests to verify cluster is ready."""
        print("\n" + "="*80)
        print("STEP 1: Running Smoke Tests")
        print("="*80)
        
        result = subprocess.run(
            [sys.executable, "tests/smoke/run_smoke_tests.py"],
            capture_output=False  # Let output stream to console
        )
        
        if result.returncode != 0:
            print("\n❌ Smoke tests failed. Cluster not ready for testing.")
            return False
            
        print("\n✅ Smoke tests passed. Cluster is ready.")
        return True
    
    def build_and_push_image(self, skip_build: bool = False) -> bool:
        """Step 2: Build and push test runner image."""
        if skip_build:
            print("\n⏭️  Skipping image build (--skip-build flag)")
            print(f"📦 Using existing image: {self.test_image}")
            return True
            
        print("\n" + "="*80)
        print("STEP 2: Building Test Runner Image")
        print("="*80)
        
        if self.production_mode:
            # Production mode: build and push to registry
            timestamp_tag = f"{self.registry}/crucible-platform:test-runner-{self.timestamp}"
            print(f"\n🔨 Building image: {timestamp_tag}")
            build_result = subprocess.run(
                ["docker", "build", "-f", "tests/Dockerfile", "-t", timestamp_tag, "-t", self.test_image, "."],
                capture_output=False
            )
            
            if build_result.returncode != 0:
                print("❌ Failed to build test image")
                return False
                
            # Push both tags to registry
            print(f"\n📤 Pushing images to registry ({self.registry})...")
            
            # Push timestamp tag
            push_result = subprocess.run(
                ["docker", "push", timestamp_tag],
                capture_output=False
            )
            if push_result.returncode != 0:
                print("❌ Failed to push timestamp-tagged image")
                return False
                
            # Push latest tag
            push_result = subprocess.run(
                ["docker", "push", self.test_image],
                capture_output=False
            )
            if push_result.returncode != 0:
                print("❌ Failed to push latest-tagged image")
                return False
        else:
            # Local mode: build and load into cluster
            print(f"\n🔨 Building local image: {self.test_image}")
            build_result = subprocess.run(
                ["docker", "build", "-f", "tests/Dockerfile", "-t", self.test_image, "."],
                capture_output=False
            )
            
            if build_result.returncode != 0:
                print("❌ Failed to build test image")
                return False
                
            # Load image into cluster (works for kind, minikube, etc.)
            print(f"\n📥 Loading image into cluster...")
            
            # Try kind first
            load_result = subprocess.run(
                ["kind", "load", "docker-image", self.test_image, "--name", "crucible"],
                capture_output=True,
                text=True
            )
            
            if load_result.returncode != 0:
                # Try minikube
                load_result = subprocess.run(
                    ["minikube", "image", "load", self.test_image],
                    capture_output=True,
                    text=True
                )
                
                if load_result.returncode != 0:
                    print("⚠️  Could not load image into cluster automatically")
                    print("   Please ensure image is available to your cluster")
                    print(f"   Image: {self.test_image}")
            
        print("✅ Test image ready")
        return True
    
    def create_coordinator_job(self, 
                             test_suites: List[str],
                             parallel: bool = False,
                             include_slow: bool = False,
                             include_destructive: bool = False,
                             test_files: List[str] = None,
                             verbose: bool = False) -> Dict:
        """Create the coordinator job manifest."""
        
        # Build command for coordinator
        coordinator_cmd = [
            "python", "/app/tests/coordinator.py",
            "--timestamp", self.timestamp,
            "--parallel" if parallel else "--sequential"
        ]
        
        if test_files:
            coordinator_cmd.extend(["--test-files"] + test_files)
        elif test_suites and test_suites != ["all"]:
            coordinator_cmd.extend(["--suites"] + test_suites)
            
        if include_slow:
            coordinator_cmd.append("--include-slow")
            
        if include_destructive:
            coordinator_cmd.append("--include-destructive")
            
        if verbose:
            coordinator_cmd.append("--verbose")
        
        # Debug: Check registry value
        print(f"\n🔍 Debug - Registry value: '{self.registry}'")
        print(f"🔍 Debug - 'ecr' in registry: {'ecr' in self.registry}")
        
        job_manifest = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": self.coordinator_job_name,
                "namespace": self.namespace,
                "labels": {
                    "app": "test-coordinator",
                    "test-run": self.timestamp
                }
            },
            "spec": {
                "backoffLimit": 0,
                "activeDeadlineSeconds": 3600,  # 1 hour timeout
                "ttlSecondsAfterFinished": 86400,  # Clean up after 24 hours
                "template": {
                    "spec": {
                        "serviceAccountName": "test-coordinator",
                        "priorityClassName": "test-coordinator-priority",
                        "containers": [{
                            "name": "coordinator",
                            "image": self.test_image,
                            "imagePullPolicy": self.image_pull_policy,
                            "env": [
                                {"name": "IN_CLUSTER", "value": "true"},
                                {"name": "K8S_NAMESPACE", "value": self.namespace},
                                {"name": "TEST_IMAGE", "value": self.test_image},
                                {"name": "PRODUCTION_MODE", "value": str(self.production_mode).lower()},
                            ],
                            "command": coordinator_cmd,
                            "resources": {
                                "requests": {
                                    "memory": "256Mi",
                                    "cpu": "100m"
                                },
                                "limits": {
                                    "memory": "512Mi",
                                    "cpu": "500m"
                                }
                            }
                        }],
                        "imagePullSecrets": [{"name": "ecr-secret"}] if "ecr" in self.registry else [],
                        "restartPolicy": "Never"
                    }
                }
            }
        }
        
        # Debug: Print the imagePullSecrets value
        print(f"🔍 Debug - imagePullSecrets: {job_manifest['spec']['template']['spec']['imagePullSecrets']}")
        
        return job_manifest
    
    def ensure_coordinator_rbac(self) -> bool:
        """Ensure the coordinator has permissions to create jobs."""
        print("\n🔐 Setting up coordinator permissions...")
        
        rbac_manifest = {
            "apiVersion": "v1",
            "kind": "List",
            "items": [
                {
                    "apiVersion": "v1",
                    "kind": "ServiceAccount",
                    "metadata": {
                        "name": "test-coordinator",
                        "namespace": self.namespace
                    }
                },
                {
                    "apiVersion": "rbac.authorization.k8s.io/v1",
                    "kind": "Role",
                    "metadata": {
                        "name": "test-coordinator",
                        "namespace": self.namespace
                    },
                    "rules": [
                        {
                            "apiGroups": ["batch"],
                            "resources": ["jobs"],
                            "verbs": ["create", "get", "list", "watch", "delete"]
                        },
                        {
                            "apiGroups": [""],
                            "resources": ["pods", "pods/log"],
                            "verbs": ["get", "list", "watch"]
                        }
                    ]
                },
                {
                    "apiVersion": "rbac.authorization.k8s.io/v1",
                    "kind": "RoleBinding",
                    "metadata": {
                        "name": "test-coordinator",
                        "namespace": self.namespace
                    },
                    "roleRef": {
                        "apiGroup": "rbac.authorization.k8s.io",
                        "kind": "Role",
                        "name": "test-coordinator"
                    },
                    "subjects": [{
                        "kind": "ServiceAccount",
                        "name": "test-coordinator",
                        "namespace": self.namespace
                    }]
                }
            ]
        }
        
        result = subprocess.run(
            ["kubectl", "apply", "-f", "-"],
            input=json.dumps(rbac_manifest),
            capture_output=True,
            text=True
        )
        
        return result.returncode == 0
    
    def submit_coordinator_job(self, job_manifest: Dict) -> bool:
        """Step 3: Submit the coordinator job to the cluster."""
        print("\n" + "="*80)
        print("STEP 3: Submitting Test Coordinator Job")
        print("="*80)
        
        # Ensure RBAC exists
        if not self.ensure_coordinator_rbac():
            print("❌ Failed to setup coordinator permissions")
            return False
        
        # Submit job
        print(f"\n🚀 Submitting coordinator job: {self.coordinator_job_name}")
        result = subprocess.run(
            ["kubectl", "apply", "-f", "-"],
            input=json.dumps(job_manifest),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ Failed to create job: {result.stderr}")
            return False
            
        print("✅ Coordinator job submitted")
        return True
    
    def monitor_coordinator(self) -> int:
        """Step 4: Monitor the coordinator job and stream logs."""
        print("\n" + "="*80)
        print("STEP 4: Monitoring Test Execution")
        print("="*80)
        
        # Wait for pod to start
        print("\n⏳ Waiting for coordinator to start...")
        for i in range(30):
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", self.namespace,
                 "-l", f"job-name={self.coordinator_job_name}", "-o", "json"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                pods = json.loads(result.stdout)
                if pods["items"] and pods["items"][0]["status"]["phase"] != "Pending":
                    break
            
            time.sleep(2)
            print(".", end="", flush=True)
        else:
            print("\n❌ Coordinator pod did not start within 60 seconds")
            return 1
        
        print("\n\n📋 Coordinator Logs:")
        print("-" * 80)
        
        # Stream logs
        log_process = subprocess.run(
            ["kubectl", "logs", "-f", f"job/{self.coordinator_job_name}", 
             "-n", self.namespace],
            capture_output=False  # Stream directly to console
        )
        
        # Wait for job to complete
        wait_result = subprocess.run(
            ["kubectl", "wait", "--for=condition=complete", 
             f"job/{self.coordinator_job_name}", "-n", self.namespace, 
             "--timeout=30s"],
            capture_output=True,
            text=True
        )
        
        # Get final job status
        result = subprocess.run(
            ["kubectl", "get", "job", self.coordinator_job_name, 
             "-n", self.namespace, "-o", "json"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            job_data = json.loads(result.stdout)
            status = job_data.get("status", {})
            succeeded = status.get("succeeded", 0)
            if succeeded > 0:
                return 0
        
        return 1
    
    def cleanup(self, exit_code=None):
        """Clean up the coordinator job."""
        print("\n🧹 Cleaning up coordinator job...")
        
        if exit_code != 0:
            print("   ⚠️  Tests failed - preserving coordinator job for debugging")
            print(f"   To view logs: kubectl logs job/{self.coordinator_job_name} -n {self.namespace}")
            print(f"   To delete: kubectl delete job {self.coordinator_job_name} -n {self.namespace}")
            print(f"   To see failed test jobs: kubectl get jobs -n {self.namespace} -l test-run={self.timestamp}")
            return
        
        subprocess.run(
            ["kubectl", "delete", "job", self.coordinator_job_name, 
             "-n", self.namespace, "--wait=false"],
            capture_output=True
        )
    
    def run(self, 
            test_suites: List[str],
            skip_build: bool = False,
            parallel: bool = False,
            include_slow: bool = False,
            include_destructive: bool = False,
            test_files: List[str] = None,
            verbose: bool = False) -> int:
        """Run the complete test orchestration pipeline."""
        
        print("\n" + "="*80)
        print("KUBERNETES TEST ORCHESTRATOR")
        print("="*80)
        print(f"\nConfiguration:")
        print(f"  Namespace: {self.namespace}")
        if self.production_mode:
            print(f"  Registry: {self.registry} ({'Docker Hub' if hasattr(self, 'docker_hub_user') and self.docker_hub_user else 'ECR'})")
        else:
            print(f"  Mode: Local (no registry)")
        print(f"  Test Image: {self.test_image}")
        if test_files:
            print(f"  Test Files: {test_files}")
        else:
            print(f"  Test Suites: {test_suites or ['all']}")
        print(f"  Parallel: {parallel}")
        print(f"  Include Slow: {include_slow}")
        print(f"  Include Destructive: {include_destructive}")
        
        try:
            # Step 1: Smoke tests
            if not self.run_smoke_tests():
                return 1
            
            # Step 2: Build image
            if not self.build_and_push_image(skip_build):
                return 1
            
            # Step 3: Create and submit coordinator job
            job_manifest = self.create_coordinator_job(
                test_suites=test_suites,
                parallel=parallel,
                include_slow=include_slow,
                include_destructive=include_destructive,
                test_files=test_files,
                verbose=verbose
            )
            
            if not self.submit_coordinator_job(job_manifest):
                return 1
            
            # Step 4: Monitor execution
            exit_code = self.monitor_coordinator()
            self.cleanup(exit_code)
            return exit_code
            
        finally:
            pass


def main():
    """Parse arguments and run orchestrator."""
    parser = argparse.ArgumentParser(
        description="Orchestrate Kubernetes test execution"
    )
    parser.add_argument(
        "suites",
        nargs="*",
        default=["all"],
        help="Test suites to run (unit, integration, e2e, etc.) or specific test files"
    )
    parser.add_argument(
        "--test-files",
        nargs="+",
        help="Specific test files to run (e.g., test_celery_connection.py)"
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip building test image"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run test suites in parallel"
    )
    parser.add_argument(
        "--include-slow",
        action="store_true",
        help="Include slow tests"
    )
    parser.add_argument(
        "--include-destructive",
        action="store_true",
        help="Include destructive tests"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show full output and logs (no truncation)"
    )
    
    args = parser.parse_args()
    
    orchestrator = TestOrchestrator()
    exit_code = orchestrator.run(
        test_suites=args.suites,
        skip_build=args.skip_build,
        parallel=args.parallel,
        include_slow=args.include_slow,
        include_destructive=args.include_destructive,
        test_files=args.test_files,
        verbose=args.verbose
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()