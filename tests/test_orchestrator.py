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
    
    def _detect_cluster_type(self) -> str:
        """Detect if we're using a local or remote cluster based on kubeconfig context."""
        try:
            # Get current context
            result = subprocess.run(
                ["kubectl", "config", "current-context"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print("⚠️  Could not detect cluster type, assuming local")
                return "local"
                
            context = result.stdout.strip().lower()
            
            # Check for local cluster indicators
            local_indicators = ["kind-", "minikube", "docker-desktop", "rancher-desktop", "k3d-", "microk8s"]
            if any(indicator in context for indicator in local_indicators):
                print(f"🏠 Detected local cluster: {result.stdout.strip()}")
                return "local"
            
            # Check for remote cluster indicators
            remote_indicators = ["eks", "gke", "aks", "arn:aws", "digitalocean", "linode", "vultr"]
            if any(indicator in context for indicator in remote_indicators):
                print(f"☁️  Detected remote cluster: {result.stdout.strip()}")
                return "remote"
            
            # If we can't determine, check the cluster endpoint
            endpoint_result = subprocess.run(
                ["kubectl", "cluster-info", "--request-timeout=2s"],
                capture_output=True,
                text=True
            )
            
            if endpoint_result.returncode == 0:
                # If it's localhost or 127.0.0.1, it's likely local
                if "localhost" in endpoint_result.stdout or "127.0.0.1" in endpoint_result.stdout:
                    print(f"🏠 Detected local cluster (localhost endpoint)")
                    return "local"
                else:
                    print(f"☁️  Detected remote cluster (external endpoint)")
                    return "remote"
            
            # Default to local if we can't determine
            print("⚠️  Could not determine cluster type, assuming local")
            return "local"
            
        except Exception as e:
            print(f"⚠️  Error detecting cluster type: {e}, assuming local")
            return "local"
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.namespace = os.environ.get("K8S_NAMESPACE", "crucible")
        
        # Detect cluster type from kubeconfig
        self.cluster_type = self._detect_cluster_type()
        
        # Check if we're in production mode or using a remote cluster
        force_production = os.environ.get("PRODUCTION_MODE", "false").lower() == "true"
        self.production_mode = force_production or self.cluster_type == "remote"
        
        if self.production_mode:
            # Production mode: use registry
            if self.cluster_type == "remote" and not force_production:
                print("🌐 Remote cluster detected - enabling registry mode")
            else:
                print("🏭 Running in PRODUCTION mode - using container registry")
            
            # Docker Hub configuration
            self.docker_hub_user = os.environ.get("DOCKER_HUB_USER")
            
            # Registry precedence: ECR > Docker Hub > Error
            if os.environ.get("ECR_REGISTRY"):
                self.registry = os.environ.get("ECR_REGISTRY")
                print(f"📦 Using ECR registry: {self.registry}")
                # Use unique tags for CI/CD
                unique_tag = os.environ.get("GITHUB_SHA", self.timestamp)[:8] if os.environ.get("GITHUB_SHA") else self.timestamp
                self.test_image = f"{self.registry}/test-runner:{unique_tag}"
                self.test_image_latest = f"{self.registry}/test-runner:latest"
            elif self.docker_hub_user:
                self.registry = "docker.io"  # Docker Hub
                self.test_image = f"{self.docker_hub_user}/crucible-test-runner:latest"
                print(f"📦 Using Docker Hub: {self.docker_hub_user}")
            else:
                if self.cluster_type == "remote":
                    raise ValueError(
                        "\n❌ Remote cluster detected but no registry configured!\n"
                        "   Please set either ECR_REGISTRY or DOCKER_HUB_USER in your .env file\n"
                        "   Or run with PRODUCTION_MODE=false to force local mode"
                    )
                else:
                    raise ValueError(
                        "No registry configured. Please set either ECR_REGISTRY or DOCKER_HUB_USER in your .env file"
                    )
            # Smart defaults: IfNotPresent for remote clusters, allow override
            default_policy = "IfNotPresent" if self.cluster_type == "remote" else "Always"
            self.image_pull_policy = os.environ.get("IMAGE_PULL_POLICY", default_policy)
        else:
            # Local mode: no registry needed
            print("🏠 Running in LOCAL mode - using local images only")
            self.registry = ""
            self.test_image = "crucible-platform/test-runner:latest"
            # For local clusters, default to Never (image must be loaded)
            # For remote clusters in local mode, this will fail - which is intentional
            self.image_pull_policy = os.environ.get("IMAGE_PULL_POLICY", "Never")
            
        self.coordinator_job_name = f"test-coordinator-{self.timestamp}"
        
        # Log configuration
        print(f"📋 Image Pull Policy: {self.image_pull_policy}")
        
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
            # When skipping build, use the latest tag instead of timestamp tag
            if hasattr(self, 'test_image_latest'):
                self.test_image = self.test_image_latest
            print(f"📦 Using existing image: {self.test_image}")
            return True
            
        print("\n" + "="*80)
        print("STEP 2: Building Test Runner Image")
        print("="*80)
        
        if self.production_mode:
            # Production mode: build and push to registry
            print(f"\n🔨 Building image: {self.test_image}")
            
            # Build with both unique and latest tags if we have both
            build_tags = ["-t", self.test_image]
            if hasattr(self, 'test_image_latest'):
                build_tags.extend(["-t", self.test_image_latest])
            
            # Build for amd64 platform when using ECR (for EKS nodes)
            build_cmd = ["docker", "build", "-f", "tests/Dockerfile"]
            if "ecr" in self.registry.lower():
                build_cmd.extend(["--platform", "linux/amd64"])
                print("🏗️  Building for linux/amd64 platform (EKS compatibility)")
            
            build_result = subprocess.run(
                build_cmd + build_tags + ["."],
                capture_output=False
            )
            
            if build_result.returncode != 0:
                print("❌ Failed to build test image")
                return False
                
            # Login to ECR if using ECR registry
            if "ecr" in self.registry.lower():
                print(f"\n🔐 Logging in to ECR...")
                region = self.registry.split('.')[3]  # Extract region from ECR URL
                login_cmd = f"aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {self.registry}"
                login_result = subprocess.run(login_cmd, shell=True, capture_output=True, text=True)
                
                if login_result.returncode != 0:
                    print(f"❌ Failed to login to ECR: {login_result.stderr}")
                    return False
                print("✅ Successfully logged in to ECR")
                
            # Push images to registry
            print(f"\n📤 Pushing images to registry ({self.registry})...")
            print("⏳ This may take several minutes depending on your upload speed...")
            
            # Get image size
            size_result = subprocess.run(
                ["docker", "images", "--format", "{{.Size}}", self.test_image],
                capture_output=True,
                text=True
            )
            if size_result.returncode == 0 and size_result.stdout.strip():
                print(f"📊 Image size: {size_result.stdout.strip()}")
            
            # Push unique tag
            print(f"\n📤 [1/2] Pushing {self.test_image}")
            print("   Watch progress in the output below...")
            push_result = subprocess.run(
                ["docker", "push", self.test_image],
                capture_output=False
            )
            if push_result.returncode != 0:
                print("❌ Failed to push unique-tagged image")
                return False
            print(f"✅ Successfully pushed {self.test_image}")
                
            # Push latest tag if we have it
            if hasattr(self, 'test_image_latest'):
                print(f"\n📤 [2/2] Pushing {self.test_image_latest}")
                print("   This should be faster (same layers)...")
                push_result = subprocess.run(
                    ["docker", "push", self.test_image_latest],
                    capture_output=False
                )
                if push_result.returncode != 0:
                    print("❌ Failed to push latest-tagged image")
                    return False
                print(f"✅ Successfully pushed {self.test_image_latest}")
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
            if self.cluster_type == "local":
                print(f"\n📥 Loading image into local cluster...")
                
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
            else:
                print("\n⚠️  WARNING: Running in local mode against a remote cluster!")
                print("   The test image exists only on your local machine.")
                print("   This will likely fail unless you manually push the image to a registry.")
                print(f"   Image: {self.test_image}")
                print("\n   Consider using PRODUCTION_MODE=true or setting ECR_REGISTRY")
            
        print("✅ Test image ready")
        return True
    
    def create_coordinator_job(self, 
                             test_suites: List[str],
                             parallel: bool = False,
                             include_slow: bool = False,
                             include_destructive: bool = False,
                             test_files: List[str] = None,
                             verbose: bool = False,
                             resource_cleanup: str = "none",
                             show_cluster_resources: bool = False) -> Dict:
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
            
        if resource_cleanup != "none":
            coordinator_cmd.extend(["--resource-cleanup", resource_cleanup])
            
        if show_cluster_resources:
            coordinator_cmd.append("--show-cluster-resources")
        
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
                        "priorityClassName": "test-infrastructure-priority",  # Priority 400 - higher than test evaluations
                        "containers": [{
                            "name": "coordinator",
                            "image": self.test_image,
                            "imagePullPolicy": self.image_pull_policy,
                            "env": [
                                {"name": "IN_CLUSTER", "value": "true"},
                                {"name": "IN_CLUSTER_TESTS", "value": "true"},
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
                        # ECR doesn't need imagePullSecrets when using IAM roles
                        "imagePullSecrets": [],
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
                        },
                        {
                            "apiGroups": [""],
                            "resources": ["nodes"],
                            "verbs": ["get", "list"]
                        },
                        {
                            "apiGroups": [""],
                            "resources": ["resourcequotas"],
                            "verbs": ["get", "list"]
                        },
                        {
                            "apiGroups": ["metrics.k8s.io"],
                            "resources": ["nodes"],
                            "verbs": ["get", "list"]
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
                },
                {
                    "apiVersion": "rbac.authorization.k8s.io/v1",
                    "kind": "ClusterRole",
                    "metadata": {
                        "name": "test-coordinator-cluster-viewer"
                    },
                    "rules": [
                        {
                            "apiGroups": [""],
                            "resources": ["nodes", "pods"],
                            "verbs": ["get", "list"]
                        },
                        {
                            "apiGroups": ["metrics.k8s.io"],
                            "resources": ["nodes"],
                            "verbs": ["get", "list"]
                        }
                    ]
                },
                {
                    "apiVersion": "rbac.authorization.k8s.io/v1",
                    "kind": "ClusterRoleBinding",
                    "metadata": {
                        "name": f"test-coordinator-{self.namespace}-cluster-viewer"
                    },
                    "roleRef": {
                        "apiGroup": "rbac.authorization.k8s.io",
                        "kind": "ClusterRole",
                        "name": "test-coordinator-cluster-viewer"
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
    
    def collect_test_results(self):
        """Collect test results from coordinator pod."""
        print("\n📦 Collecting test results...")
        
        # Create results directory
        results_dir = f"test-results-{self.timestamp}"
        os.makedirs(results_dir, exist_ok=True)
        
        # Get pod name
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", self.namespace,
             "-l", f"job-name={self.coordinator_job_name}", "-o", "jsonpath={.items[0].metadata.name}"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            pod_name = result.stdout.strip()
            
            # Try to copy test results
            subprocess.run(
                ["kubectl", "cp", f"{self.namespace}/{pod_name}:/app/test-results/.", results_dir],
                capture_output=True
            )
            
            # Save logs
            log_file = os.path.join(results_dir, "coordinator.log")
            with open(log_file, "w") as f:
                subprocess.run(
                    ["kubectl", "logs", f"job/{self.coordinator_job_name}", "-n", self.namespace],
                    stdout=f
                )
            
            print(f"✅ Test results saved to {results_dir}/")
            
    def monitor_coordinator(self) -> int:
        """Step 4: Monitor the coordinator job and stream logs."""
        print("\n" + "="*80)
        print("STEP 4: Monitoring Test Execution")
        print("="*80)
        
        # Wait for pod to start
        print("\n⏳ Waiting for coordinator pod to start...")
        print("   Checking pod status every 2 seconds...")
        
        start_time = time.time()
        last_phase = None
        last_reason = None
        
        for i in range(300):  # 10 minutes timeout for large image pulls
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", self.namespace,
                 "-l", f"job-name={self.coordinator_job_name}", "-o", "json"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                pods = json.loads(result.stdout)
                if pods["items"]:
                    pod = pods["items"][0]
                    phase = pod["status"]["phase"]
                    
                    # Get container status for more detail
                    container_statuses = pod["status"].get("containerStatuses", [])
                    if container_statuses:
                        container = container_statuses[0]
                        if "waiting" in container["state"]:
                            reason = container["state"]["waiting"].get("reason", "Unknown")
                            if reason != last_reason:
                                elapsed = int(time.time() - start_time)
                                print(f"\n   [{elapsed}s] Container waiting: {reason}")
                                
                                # Provide helpful hints for common issues
                                if reason == "ErrImagePull" or reason == "ImagePullBackOff":
                                    print("   💡 Image pull failing - check ECR permissions or image existence")
                                elif reason == "ContainerCreating":
                                    print("   💡 Container is being created - this is normal")
                                
                                last_reason = reason
                    
                    # Check if phase changed
                    if phase != last_phase:
                        elapsed = int(time.time() - start_time)
                        print(f"\n   [{elapsed}s] Pod phase: {phase}")
                        last_phase = phase
                    
                    # Break if pod is running
                    if phase != "Pending":
                        print(f"\n✅ Pod started after {int(time.time() - start_time)} seconds")
                        break
                else:
                    # No pods yet
                    if i == 0:
                        print("   Waiting for pod to be created...")
            
            time.sleep(2)
            print(".", end="", flush=True)
        else:
            elapsed = int(time.time() - start_time)
            print(f"\n❌ Coordinator pod did not start within {elapsed} seconds")
            
            # Get more diagnostic info
            print("\n🔍 Diagnostic information:")
            subprocess.run(
                ["kubectl", "describe", "job", self.coordinator_job_name, "-n", self.namespace],
                capture_output=False
            )
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
        
        # Save test results if available
        self.collect_test_results()
        
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
    
    def run_local_tests(self, 
                       test_suites: List[str],
                       test_files: List[str] = None,
                       include_slow: bool = False,
                       include_destructive: bool = False,
                       verbose: bool = False) -> int:
        """Run tests locally without Kubernetes."""
        print("\n" + "="*80)
        print("LOCAL TEST RUNNER")
        print("="*80)
        print("\n🏠 Running tests locally (no Kubernetes required)")
        
        # Build pytest command using the current Python interpreter
        # This ensures we use the venv Python if it's activated
        pytest_cmd = [sys.executable, "-m", "pytest"]
        
        # Add test paths
        if test_files:
            # Run specific test files
            for test_file in test_files:
                pytest_cmd.append(f"tests/{test_file}")
        else:
            # Run test suites
            for suite in test_suites:
                if suite == "all":
                    pytest_cmd.append("tests/")
                    break
                else:
                    pytest_cmd.append(f"tests/{suite}/")
        
        # Add pytest arguments
        pytest_cmd.extend(["-v", "--tb=short"])
        
        # Handle markers
        markers = []
        if not include_slow:
            markers.append("not slow")
        if not include_destructive:
            markers.append("not destructive")
        
        # When running unit tests locally, only run tests marked as unit
        if "unit" in test_suites:
            markers.append("unit")
        
        if markers:
            pytest_cmd.extend(["-m", " and ".join(markers)])
        
        if verbose:
            pytest_cmd.append("-s")  # No capture, show print statements
        
        # Run tests
        print(f"\n🧪 Running: {' '.join(pytest_cmd)}")
        result = subprocess.run(pytest_cmd)
        
        return result.returncode
    
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
            verbose: bool = False,
            resource_cleanup: str = "none",
            local: str = "true",
            show_cluster_resources: bool = False) -> int:
        """Run the complete test orchestration pipeline."""
        
        # Separate unit tests from other suites
        run_unit_locally = "unit" in test_suites and local != "false"
        cluster_suites = [s for s in test_suites if s != "unit" or local == "false"]
        
        exit_code = 0
        
        # Run unit tests locally if requested
        if run_unit_locally:
            print("\n🏠 Running unit tests locally first...")
            exit_code = self.run_local_tests(
                test_suites=["unit"],
                test_files=test_files,
                include_slow=include_slow,
                include_destructive=include_destructive,
                verbose=verbose
            )
            if exit_code != 0:
                return exit_code
        
        # If no cluster tests needed, we're done
        if not cluster_suites:
            return exit_code
        
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
            print(f"  Test Suites: {cluster_suites if cluster_suites else ['none']}")
        print(f"  Parallel: {parallel}")
        print(f"  Include Slow: {include_slow}")
        print(f"  Include Destructive: {include_destructive}")
        if resource_cleanup != "none":
            print(f"  Resource Cleanup: {resource_cleanup} (clean between tests)")
        
        try:
            # Step 1: Smoke tests
            if not self.run_smoke_tests():
                return 1
            
            # Step 2: Build image
            if not self.build_and_push_image(skip_build):
                return 1
            
            # Step 3: Create and submit coordinator job
            job_manifest = self.create_coordinator_job(
                test_suites=cluster_suites,
                parallel=parallel,
                include_slow=include_slow,
                include_destructive=include_destructive,
                test_files=test_files,
                verbose=verbose,
                resource_cleanup=resource_cleanup,
                show_cluster_resources=show_cluster_resources
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
        "--verbose", "-v",
        action="store_true",
        help="Show full output and logs (no truncation)"
    )
    parser.add_argument(
        "--resource-cleanup",
        choices=["none", "pods", "all"],
        default="none",
        help="Resource cleanup level between tests (none, pods, or all)"
    )
    parser.add_argument(
        "--local",
        type=str,
        choices=["true", "false", "auto"],
        default="auto",
        help="Run tests locally without Kubernetes cluster. auto=local for unit tests, cluster for others (default: auto)"
    )
    parser.add_argument(
        "--show-cluster-resources",
        action="store_true",
        help="Show cluster resource usage every 5 seconds during test execution"
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
        verbose=args.verbose,
        resource_cleanup=args.resource_cleanup,
        local=args.local,
        show_cluster_resources=args.show_cluster_resources
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()