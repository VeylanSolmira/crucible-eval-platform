"""
Test Resource Manager for Kubernetes resource cleanup and tracking.

This module provides decorators and context managers to ensure proper
resource cleanup between tests while preserving logs for debugging.
"""

import functools
import subprocess
import time
import os
import pytest
from typing import Set, Dict, List, Optional
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class KubernetesResourceManager:
    """Manages Kubernetes resources created during tests."""
    
    def __init__(self, namespace: str = "crucible", preserve_on_failure: bool = True):
        self.namespace = namespace
        self.preserve_on_failure = preserve_on_failure
        self.tracked_resources: Dict[str, Set[str]] = {
            "jobs": set(),
            "pods": set(),
            "configmaps": set(),
        }
        self.test_labels: Dict[str, str] = {}
        
    def track_resource(self, resource_type: str, name: str):
        """Track a resource for cleanup."""
        self.tracked_resources[resource_type].add(name)
        
    def add_test_label(self, key: str, value: str):
        """Add a label to track resources for this test."""
        self.test_labels[key] = value
        
    def cleanup_pods(self, selector: Optional[str] = None):
        """Delete pods while preserving jobs for log access."""
        if selector:
            cmd = ["kubectl", "delete", "pods", "-n", self.namespace, "-l", selector, "--ignore-not-found=true"]
        else:
            # Clean up all evaluation pods
            cmd = ["kubectl", "delete", "pods", "-n", self.namespace, "-l", "app=evaluation", "--ignore-not-found=true"]
            
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout:
            logger.info(f"Cleaned up pods: {result.stdout}")
            
    def cleanup_jobs(self, selector: Optional[str] = None, force: bool = False):
        """Delete jobs (only if force=True or test passed)."""
        if not force and self.preserve_on_failure:
            logger.info("Preserving jobs for debugging (test may have failed)")
            return
            
        if selector:
            cmd = ["kubectl", "delete", "jobs", "-n", self.namespace, "-l", selector, "--ignore-not-found=true"]
        else:
            cmd = ["kubectl", "delete", "jobs", "-n", self.namespace, "-l", "app=evaluation", "--ignore-not-found=true"]
            
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout:
            logger.info(f"Cleaned up jobs: {result.stdout}")
            
    def wait_for_resource_cleanup(self, timeout: int = 10):
        """Wait for resources to be fully cleaned up."""
        start = time.time()
        while time.time() - start < timeout:
            # Check if pods are gone
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", self.namespace, "-l", "app=evaluation", "--no-headers"],
                capture_output=True, text=True
            )
            if not result.stdout.strip():
                return True
            time.sleep(0.5)
        return False
        
    def get_resource_usage(self) -> Dict[str, any]:
        """Get current resource usage from quota."""
        result = subprocess.run(
            ["kubectl", "get", "resourcequota", "evaluation-quota", "-n", self.namespace, "-o", "json"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            import json
            quota = json.loads(result.stdout)
            return quota.get("status", {}).get("used", {})
        return {}


@contextmanager
def managed_test_resources(test_name: str, cleanup_level: str = "pods", wait_after_cleanup: int = 3):
    """
    Context manager for test resource management.
    
    Args:
        test_name: Name of the test for labeling
        cleanup_level: "none", "pods", or "all" (includes jobs)
        wait_after_cleanup: Seconds to wait after cleanup
    """
    manager = KubernetesResourceManager()
    test_passed = False
    
    # Add test label for tracking
    test_id = f"{test_name}-{int(time.time())}"
    manager.add_test_label("test-name", test_name)
    manager.add_test_label("test-id", test_id)
    
    # Log initial state
    initial_resources = manager.get_resource_usage()
    logger.info(f"Starting {test_name} with resources: {initial_resources}")
    
    try:
        yield manager
        test_passed = True
    finally:
        # Cleanup based on level and test result
        if cleanup_level != "none":
            if cleanup_level in ["pods", "all"]:
                manager.cleanup_pods()
                
            if cleanup_level == "all" and test_passed:
                manager.cleanup_jobs()
                
            # Wait for cleanup to take effect
            if wait_after_cleanup > 0:
                manager.wait_for_resource_cleanup(wait_after_cleanup)
                
        # Log final state
        final_resources = manager.get_resource_usage()
        logger.info(f"Finished {test_name} with resources: {final_resources}")


def with_resource_cleanup(cleanup_level: str = "pods", wait_after: int = 3):
    """
    Decorator for automatic resource cleanup after tests.
    
    Usage:
        @with_resource_cleanup(cleanup_level="pods")
        def test_something():
            # test code
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with managed_test_resources(func.__name__, cleanup_level, wait_after):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Pytest fixtures for easier integration
@pytest.fixture
def resource_manager(request):
    """Pytest fixture that provides resource manager with automatic cleanup."""
    cleanup_level = request.config.getoption("--cleanup-level", default="pods")
    
    with managed_test_resources(request.node.name, cleanup_level) as manager:
        yield manager


def pytest_addoption(parser):
    """Add command-line options for resource management."""
    parser.addoption(
        "--cleanup-level",
        action="store",
        default="pods",
        choices=["none", "pods", "all"],
        help="Level of resource cleanup between tests"
    )
    parser.addoption(
        "--preserve-failed",
        action="store_true",
        default=True,
        help="Preserve resources when tests fail"
    )