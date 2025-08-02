#!/usr/bin/env python3
"""
Kubernetes pod resilience chaos testing.

Tests the platform's ability to handle pod deletions, scaling events,
and service disruptions in Kubernetes deployments.

These tests are marked as 'destructive' because they delete pods and scale services.
Run with: pytest -m destructive tests/chaos/kubernetes/test_pod_resilience.py

WARNING: These tests will disrupt services in the target namespace!
Only run in test environments.
"""

import pytest
import subprocess
import time
import asyncio
import json
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Only run if we have kubectl access
pytest.importorskip("kubernetes")
from kubernetes import client, config

logger = logging.getLogger(__name__)

# Configuration
NAMESPACE = "crucible"
API_SERVICE = "api-service"
DISPATCHER_SERVICE = "dispatcher"
STORAGE_WORKER = "storage-worker"
CELERY_WORKER = "celery-worker"

# Mark all tests in this module as destructive chaos tests
pytestmark = [pytest.mark.chaos, pytest.mark.destructive, pytest.mark.kubernetes]


@pytest.fixture(scope="session")
def k8s_client():
    """Initialize Kubernetes client."""
    try:
        # Try in-cluster config first (when running inside k8s)
        config.load_incluster_config()
    except:
        # Fall back to kubeconfig
        config.load_kube_config()
    
    return {
        "core": client.CoreV1Api(),
        "apps": client.AppsV1Api(),
        "batch": client.BatchV1Api()
    }


@pytest.fixture
def ensure_healthy_cluster(k8s_client):
    """Ensure cluster is healthy before and after tests."""
    # Check health before test
    check_deployment_health(k8s_client["apps"], NAMESPACE)
    
    yield
    
    # Restore health after test
    restore_deployments(k8s_client["apps"], NAMESPACE)
    time.sleep(10)  # Give pods time to start
    check_deployment_health(k8s_client["apps"], NAMESPACE)


def check_deployment_health(apps_v1: client.AppsV1Api, namespace: str):
    """Verify all deployments are healthy."""
    deployments = apps_v1.list_namespaced_deployment(namespace=namespace)
    
    for deployment in deployments.items:
        if deployment.status.ready_replicas != deployment.spec.replicas:
            pytest.skip(f"Deployment {deployment.metadata.name} not healthy")


def restore_deployments(apps_v1: client.AppsV1Api, namespace: str):
    """Restore all deployments to their desired replica count."""
    deployments = apps_v1.list_namespaced_deployment(namespace=namespace)
    
    for deployment in deployments.items:
        if deployment.status.ready_replicas != deployment.spec.replicas:
            logger.info(f"Restoring {deployment.metadata.name} to {deployment.spec.replicas} replicas")
            apps_v1.patch_namespaced_deployment_scale(
                name=deployment.metadata.name,
                namespace=namespace,
                body={"spec": {"replicas": deployment.spec.replicas}}
            )


def run_kubectl(cmd: str) -> subprocess.CompletedProcess:
    """Run kubectl command and return result."""
    full_cmd = f"kubectl {cmd}"
    logger.info(f"Running: {full_cmd}")
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        logger.error(f"Command failed: {result.stderr}")
    
    return result


from utils.utils import submit_evaluation as base_submit_evaluation

def submit_evaluation(priority: int = 0) -> Optional[str]:
    """Submit an evaluation and return its ID."""
    try:
        code = f"import time; print('Chaos test evaluation - priority {priority}'); time.sleep(5); print('Done')"
        return base_submit_evaluation(code, priority=priority)
    except Exception as e:
        logger.error(f"Failed to submit evaluation: {e}")
        return None


def wait_for_evaluation(eval_id: str, timeout: int = 120) -> Dict[str, Any]:
    """Wait for evaluation to complete and return final status."""
    port_forward = subprocess.Popen(
        f"kubectl port-forward -n {NAMESPACE} service/{API_SERVICE} 8080:8080",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    try:
        time.sleep(2)  # Wait for port forward
        
        import requests
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = requests.get(f"{api_url}/eval/{eval_id}")
            
            if response.status_code == 200:
                data = response.json()
                if data["status"] in ["completed", "failed", "cancelled"]:
                    return data
            
            time.sleep(2)
        
        return {"status": "timeout", "eval_id": eval_id}
        
    finally:
        port_forward.terminate()


@pytest.mark.asyncio
async def test_api_pod_deletion_during_submission(k8s_client, ensure_healthy_cluster):
    """Test evaluation handling when API pod is deleted during submission."""
    core_v1 = k8s_client["core"]
    
    # Submit evaluation
    eval_id = submit_evaluation(priority=1)
    assert eval_id is not None, "Failed to submit evaluation"
    
    # Delete API pod
    pods = core_v1.list_namespaced_pod(
        namespace=NAMESPACE,
        label_selector=f"app={API_SERVICE}"
    )
    
    if pods.items:
        pod_name = pods.items[0].metadata.name
        logger.info(f"Deleting API pod: {pod_name}")
        core_v1.delete_namespaced_pod(name=pod_name, namespace=NAMESPACE)
        
        # Wait for pod to be recreated
        time.sleep(10)
    
    # Verify evaluation still completes
    result = wait_for_evaluation(eval_id)
    assert result["status"] == "completed", f"Evaluation failed after API pod deletion: {result}"


@pytest.mark.asyncio
async def test_dispatcher_failure_during_processing(k8s_client, ensure_healthy_cluster):
    """Test evaluation handling when dispatcher is scaled down during processing."""
    apps_v1 = k8s_client["apps"]
    
    # Submit multiple evaluations
    eval_ids = []
    for i in range(3):
        eval_id = submit_evaluation(priority=i)
        if eval_id:
            eval_ids.append(eval_id)
        time.sleep(1)
    
    assert len(eval_ids) >= 2, "Failed to submit enough evaluations"
    
    # Scale down dispatcher
    logger.info("Scaling down dispatcher to 0")
    apps_v1.patch_namespaced_deployment_scale(
        name=DISPATCHER_SERVICE,
        namespace=NAMESPACE,
        body={"spec": {"replicas": 0}}
    )
    
    # Wait a bit
    time.sleep(15)
    
    # Scale back up
    logger.info("Scaling dispatcher back to 1")
    apps_v1.patch_namespaced_deployment_scale(
        name=DISPATCHER_SERVICE,
        namespace=NAMESPACE,
        body={"spec": {"replicas": 1}}
    )
    
    # Wait for all evaluations to complete
    results = []
    for eval_id in eval_ids:
        result = wait_for_evaluation(eval_id)
        results.append(result)
    
    # At least some should complete
    completed = [r for r in results if r["status"] == "completed"]
    assert len(completed) > 0, "No evaluations completed after dispatcher restart"


@pytest.mark.asyncio
async def test_storage_worker_pod_deletion(k8s_client, ensure_healthy_cluster):
    """Test data persistence when storage worker pod is deleted."""
    core_v1 = k8s_client["core"]
    
    # Submit evaluation
    eval_id = submit_evaluation(priority=0)
    assert eval_id is not None, "Failed to submit evaluation"
    
    # Wait for it to start processing
    time.sleep(5)
    
    # Delete storage worker pod
    pods = core_v1.list_namespaced_pod(
        namespace=NAMESPACE,
        label_selector=f"app={STORAGE_WORKER}"
    )
    
    if pods.items:
        pod_name = pods.items[0].metadata.name
        logger.info(f"Deleting storage worker pod: {pod_name}")
        core_v1.delete_namespaced_pod(name=pod_name, namespace=NAMESPACE)
    
    # Verify evaluation still completes with proper status
    result = wait_for_evaluation(eval_id)
    assert result["status"] in ["completed", "failed"], f"Unexpected status: {result}"
    
    # Verify we can still retrieve the evaluation data
    assert result.get("eval_id") == eval_id
    assert result.get("code") is not None


@pytest.mark.asyncio
async def test_multiple_component_failures(k8s_client, ensure_healthy_cluster):
    """Test system resilience with multiple component failures."""
    core_v1 = k8s_client["core"]
    apps_v1 = k8s_client["apps"]
    
    # Submit high-priority evaluation
    eval_id = submit_evaluation(priority=10)
    assert eval_id is not None, "Failed to submit evaluation"
    
    # Cause multiple failures
    logger.info("Inducing multiple component failures")
    
    # 1. Delete celery worker pod
    pods = core_v1.list_namespaced_pod(
        namespace=NAMESPACE,
        label_selector=f"app={CELERY_WORKER}"
    )
    if pods.items:
        core_v1.delete_namespaced_pod(
            name=pods.items[0].metadata.name,
            namespace=NAMESPACE
        )
    
    # 2. Scale down storage worker
    apps_v1.patch_namespaced_deployment_scale(
        name=STORAGE_WORKER,
        namespace=NAMESPACE,
        body={"spec": {"replicas": 0}}
    )
    
    # Wait a bit
    time.sleep(10)
    
    # Restore storage worker
    apps_v1.patch_namespaced_deployment_scale(
        name=STORAGE_WORKER,
        namespace=NAMESPACE,
        body={"spec": {"replicas": 1}}
    )
    
    # Verify high-priority evaluation still completes
    result = wait_for_evaluation(eval_id, timeout=180)
    assert result["status"] == "completed", f"High-priority evaluation failed during chaos: {result}"


@pytest.mark.asyncio
async def test_rapid_pod_cycling(k8s_client, ensure_healthy_cluster):
    """Test system behavior during rapid pod deletion cycles."""
    core_v1 = k8s_client["core"]
    
    # Submit evaluations
    eval_ids = []
    for i in range(5):
        eval_id = submit_evaluation(priority=i % 3)
        if eval_id:
            eval_ids.append(eval_id)
    
    assert len(eval_ids) >= 3, "Failed to submit enough evaluations"
    
    # Rapidly cycle through deleting different pods
    components = [API_SERVICE, DISPATCHER_SERVICE, CELERY_WORKER]
    
    for component in components:
        pods = core_v1.list_namespaced_pod(
            namespace=NAMESPACE,
            label_selector=f"app={component}"
        )
        
        if pods.items:
            pod_name = pods.items[0].metadata.name
            logger.info(f"Deleting {component} pod: {pod_name}")
            core_v1.delete_namespaced_pod(name=pod_name, namespace=NAMESPACE)
            time.sleep(5)  # Brief pause between deletions
    
    # Check evaluation results
    results = []
    for eval_id in eval_ids:
        result = wait_for_evaluation(eval_id, timeout=180)
        results.append(result)
    
    # Verify majority complete successfully
    completed = [r for r in results if r["status"] == "completed"]
    completion_rate = len(completed) / len(results)
    
    assert completion_rate >= 0.6, f"Only {completion_rate*100}% completed during rapid cycling"
    logger.info(f"Chaos test completed: {len(completed)}/{len(results)} evaluations succeeded")


if __name__ == "__main__":
    # Run with specific test
    pytest.main([__file__, "-v", "-s", "-m", "destructive"])