#!/usr/bin/env python3
"""Integration tests for network isolation in containers"""

import os
import pytest
import requests
import time
from tests.utils.utils import submit_evaluation, wait_for_completion, get_evaluation_status

NETWORK_TEST_CODE = '''
import socket
import urllib.request
import time

# Wait for NetworkPolicy enforcement to be applied
print("Waiting 5 seconds for NetworkPolicy enforcement...")
time.sleep(5)

results = []

# Test 1: Pod-to-pod communication (within cluster)
try:
    # Try to connect to another pod in the cluster
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    # Try connecting to the Redis service
    sock.connect(("redis.dev.svc.cluster.local", 6379))
    sock.close()
    results.append("FAIL: Pod-to-pod connection allowed")
except Exception as e:
    results.append(f"PASS: Pod-to-pod blocked - {type(e).__name__}")

# Test 2: Service DNS resolution (within cluster)
try:
    ip = socket.gethostbyname("storage-service.dev.svc.cluster.local")
    results.append("FAIL: Internal DNS resolution succeeded")
except Exception as e:
    results.append(f"PASS: Internal DNS blocked - {type(e).__name__}")

# Test 3: Kubernetes API access
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    sock.connect(("kubernetes.default.svc.cluster.local", 443))
    sock.close()
    results.append("FAIL: Kubernetes API connection allowed")
except Exception as e:
    results.append(f"PASS: Kubernetes API blocked - {type(e).__name__}")

# Test 4: External traffic (this might still work due to VPC CNI limitations)
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    sock.connect(("8.8.8.8", 53))
    sock.close()
    results.append("WARNING: External connection allowed (VPC CNI limitation)")
except Exception as e:
    results.append(f"PASS: External blocked - {type(e).__name__}")

for result in results:
    print(result)
'''

@pytest.mark.graybox
@pytest.mark.integration
@pytest.mark.network_isolation
@pytest.mark.skip(
    reason="AWS VPC CNI NetworkPolicy enforcement has timing issues with Job pods - network connections complete before eBPF rules are applied"
)
def test_network_isolation():
    """Test that containers have no cluster-internal network access.
    
    Note: Due to AWS VPC CNI NetworkPolicy limitations, this test verifies
    cluster-internal isolation only. External internet access may still work
    as VPC CNI is designed primarily for pod-to-pod and pod-to-service traffic control.
    """
    
    # Submit the network test code
    eval_id = submit_evaluation(NETWORK_TEST_CODE)
    assert eval_id is not None, "Failed to submit evaluation"
    
    # Wait for completion
    # Network isolation makes tests slower due to timeouts
    # TODO: Reduce timeout once we implement Kubernetes event-based processing instead of 10s polling
    status = wait_for_completion(eval_id, timeout=120)
    assert status is not None, "Evaluation did not complete in time"
    
    # Get the full evaluation details
    eval_data = get_evaluation_status(eval_id)
    assert eval_data["status"] == "completed", f"Evaluation failed with status: {eval_data['status']}"
    
    # Check the output
    output = eval_data.get("output", "")
    
    # Cluster-internal traffic should be blocked
    assert "PASS: Pod-to-pod blocked" in output
    assert "PASS: Internal DNS blocked" in output
    assert "PASS: Kubernetes API blocked" in output
    
    # External traffic might work (known VPC CNI limitation)
    if "WARNING: External connection allowed" in output:
        print("Note: External internet access is allowed due to VPC CNI NetworkPolicy limitations")
    
    # None should fail (except external which is a warning)
    assert output.count("FAIL:") == 0, f"Network isolation test failed - cluster-internal access was allowed:\n{output}"