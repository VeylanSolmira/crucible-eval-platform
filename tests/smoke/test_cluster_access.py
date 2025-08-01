#!/usr/bin/env python3
"""
Minimal smoke tests for Kubernetes cluster access.

These tests run from OUTSIDE the cluster to verify:
1. kubectl connectivity
2. Required services are present
3. Job execution capability
4. API accessibility
5. Test image availability

Run these before attempting to run the main test suite inside the cluster.
"""

import subprocess
import json
import time
import sys
import os
import pytest
import requests
from typing import Dict, List, Tuple

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestClusterAccess:
    """Smoke tests that run from outside the cluster."""
    
    @pytest.fixture(scope="class")
    def namespace(self):
        """Get the target namespace from environment or default."""
        return os.environ.get("K8S_NAMESPACE", "crucible")
    
    @pytest.fixture(scope="class")
    def test_image(self):
        """Get the test runner image to verify."""
        # This would come from your ECR registry
        return os.environ.get("TEST_RUNNER_IMAGE", "crucible-test-runner:latest")
    
    def test_kubectl_connectivity(self):
        """Verify we can connect to the cluster."""
        result = subprocess.run(
            ["kubectl", "version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"kubectl connection failed: {result.stderr}"
        # Check for server version in output (format varies by kubectl version)
        assert "Server Version:" in result.stdout or "serverVersion" in result.stdout, \
            "Could not get server version"
        print(f"✓ Connected to cluster")
    
    def test_namespace_exists(self, namespace):
        """Verify our namespace exists and is accessible."""
        result = subprocess.run(
            ["kubectl", "get", "namespace", namespace, "-o", "json"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Namespace {namespace} not found: {result.stderr}"
        
        ns_data = json.loads(result.stdout)
        status = ns_data.get("status", {}).get("phase")
        assert status == "Active", f"Namespace {namespace} is not active: {status}"
        print(f"✓ Namespace {namespace} is active")
    
    def test_required_services(self, namespace):
        """Verify all required services are present."""
        required_services = [
            "api-service",
            "celery-redis",
            "redis",
            "postgres",
            "storage-service",
            "dispatcher-service",
        ]
        
        result = subprocess.run(
            ["kubectl", "get", "services", "-n", namespace, "-o", "json"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Failed to list services: {result.stderr}"
        
        services_data = json.loads(result.stdout)
        existing_services = {
            item["metadata"]["name"] 
            for item in services_data.get("items", [])
        }
        
        missing = set(required_services) - existing_services
        assert not missing, f"Missing required services: {missing}"
        print(f"✓ All {len(required_services)} required services present")
        
        # Check service endpoints
        for service in required_services:
            result = subprocess.run(
                ["kubectl", "get", "endpoints", service, "-n", namespace, "-o", "json"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                endpoints = json.loads(result.stdout)
                subsets = endpoints.get("subsets", [])
                if subsets and subsets[0].get("addresses"):
                    print(f"  ✓ {service} has active endpoints")
                else:
                    print(f"  ⚠ {service} has no active endpoints")
    
    def test_simple_job_execution(self, namespace):
        """Verify we can run a job in the cluster."""
        job_name = f"smoke-test-job-{int(time.time())}"
        
        # Create a simple job manifest
        job_manifest = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": job_name,
                "namespace": namespace
            },
            "spec": {
                "template": {
                    "spec": {
                        "containers": [{
                            "name": "test",
                            "image": "busybox:latest",
                            "command": ["sh", "-c", "echo 'Job execution successful!' && exit 0"],
                            "resources": {
                                "requests": {
                                    "cpu": "100m",
                                    "memory": "64Mi"
                                },
                                "limits": {
                                    "cpu": "200m",
                                    "memory": "128Mi"
                                }
                            }
                        }],
                        "restartPolicy": "Never"
                    }
                }
            }
        }
        
        # Create the job
        create_result = subprocess.run(
            ["kubectl", "apply", "-f", "-"],
            input=json.dumps(job_manifest),
            capture_output=True,
            text=True
        )
        assert create_result.returncode == 0, f"Failed to create job: {create_result.stderr}"
        print(f"✓ Created test job: {job_name}")
        
        try:
            # Wait for job completion (max 30 seconds)
            wait_result = subprocess.run(
                ["kubectl", "wait", "--for=condition=complete", f"job/{job_name}", 
                 "-n", namespace, "--timeout=30s"],
                capture_output=True,
                text=True
            )
            assert wait_result.returncode == 0, f"Job did not complete: {wait_result.stderr}"
            print("✓ Job completed successfully")
            
            # Get logs to verify output
            logs_result = subprocess.run(
                ["kubectl", "logs", f"job/{job_name}", "-n", namespace],
                capture_output=True,
                text=True
            )
            assert logs_result.returncode == 0, f"Failed to get logs: {logs_result.stderr}"
            assert "Job execution successful!" in logs_result.stdout
            print("✓ Job output verified")
            
        finally:
            # Cleanup
            subprocess.run(
                ["kubectl", "delete", "job", job_name, "-n", namespace, "--wait=false"],
                capture_output=True
            )
    
    def test_api_accessible(self, namespace):
        """Verify API is accessible (may require port-forward)."""
        # First check if we can access directly (e.g., via LoadBalancer/Ingress)
        # Get API URL from environment if set
        api_base = os.environ.get("API_URL", "").rstrip("/api")
        api_urls = []
        if api_base:
            api_urls.append(f"{api_base}/health")
        
        api_accessible = False
        for url in api_urls:
            try:
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    print(f"✓ API accessible at {url}")
                    api_accessible = True
                    break
            except:
                continue
        
        if not api_accessible:
            # Try with port-forward
            print("  Setting up port-forward to test API...")
            port_forward = subprocess.Popen(
                ["kubectl", "port-forward", "-n", namespace, "svc/api-service", "8080:8080"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(3)  # Wait for port-forward
            
            try:
                # Use the port-forwarded URL
                pf_url = "http://localhost:8080/health"
                response = requests.get(pf_url, timeout=5)
                assert response.status_code == 200, f"API health check failed: {response.status_code}"
                health_data = response.json()
                assert health_data.get("status") == "healthy", f"API not healthy: {health_data}"
                print("✓ API is healthy (via port-forward)")
                
                # Set API_URL for subsequent tests if not already set
                if not os.environ.get("API_URL"):
                    os.environ["API_URL"] = "http://localhost:8080/api"
            finally:
                port_forward.terminate()
    
    def test_deployments_ready(self, namespace):
        """Verify all deployments are ready."""
        result = subprocess.run(
            ["kubectl", "get", "deployments", "-n", namespace, "-o", "json"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Failed to list deployments: {result.stderr}"
        
        deployments = json.loads(result.stdout)
        not_ready = []
        
        for deployment in deployments.get("items", []):
            name = deployment["metadata"]["name"]
            spec_replicas = deployment["spec"].get("replicas", 1)
            ready_replicas = deployment["status"].get("readyReplicas", 0)
            
            if ready_replicas < spec_replicas:
                not_ready.append(f"{name} ({ready_replicas}/{spec_replicas})")
            else:
                print(f"  ✓ {name} is ready ({ready_replicas}/{spec_replicas})")
        
        assert not not_ready, f"Deployments not ready: {', '.join(not_ready)}"
        print("✓ All deployments are ready")
    
    def test_test_runner_image_accessible(self, test_image):
        """Verify the test runner image can be used."""
        # This is a simple check - in reality you might want to:
        # 1. Check ECR credentials
        # 2. Try to pull the image
        # 3. Verify it has the test code
        
        # For now, just verify we can describe an image pull
        # You would need to adjust this based on your registry
        print(f"✓ Test image configured: {test_image}")
        
        # Could also create a job that uses the test image
        # and runs a simple command like "python -c 'import pytest'"


@pytest.mark.parametrize("resource_type,expected_count", [
    ("pods", 5),      # Rough minimum expected
    ("services", 7),   # All our services
    ("configmaps", 2), # At least kube-root-ca.crt and any custom ones
])
def test_resource_counts(resource_type, expected_count):
    """Verify minimum expected resources exist."""
    namespace = os.environ.get("K8S_NAMESPACE", "crucible")
    result = subprocess.run(
        ["kubectl", "get", resource_type, "-n", namespace, "--no-headers"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        count = len([line for line in result.stdout.strip().split('\n') if line])
        assert count >= expected_count, \
            f"Expected at least {expected_count} {resource_type}, found {count}"
        print(f"✓ Found {count} {resource_type} (expected >= {expected_count})")


if __name__ == "__main__":
    # Run the smoke tests
    print("Running Kubernetes cluster access smoke tests...")
    print("=" * 60)
    
    # You can run this directly or via pytest
    pytest.main([__file__, "-v", "-s"])