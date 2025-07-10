#!/usr/bin/env python3
"""Integration tests for network isolation in containers"""

import pytest
import requests
import time
from tests.utils import submit_evaluation, wait_for_completion, get_evaluation_status

NETWORK_TEST_CODE = '''
import socket
import urllib.request

results = []

# Test 1: Direct socket connection
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    sock.connect(("8.8.8.8", 53))  # Google DNS
    sock.close()
    results.append("FAIL: Socket connection allowed")
except Exception as e:
    results.append(f"PASS: Socket blocked - {type(e).__name__}")

# Test 2: HTTP request
try:
    response = urllib.request.urlopen("http://example.com", timeout=2)
    results.append("FAIL: HTTP request succeeded")
except Exception as e:
    results.append(f"PASS: HTTP blocked - {type(e).__name__}")

# Test 3: DNS resolution
try:
    ip = socket.gethostbyname("google.com")
    results.append("FAIL: DNS resolution succeeded")
except Exception as e:
    results.append(f"PASS: DNS blocked - {type(e).__name__}")

for result in results:
    print(result)
'''

@pytest.mark.integration
def test_network_isolation():
    """Test that containers have no network access"""
    # Submit the network test code
    eval_id = submit_evaluation(NETWORK_TEST_CODE)
    assert eval_id is not None, "Failed to submit evaluation"
    
    # Wait for completion
    status = wait_for_completion(eval_id, timeout=30)
    assert status is not None, "Evaluation did not complete in time"
    
    # Get the full evaluation details
    eval_data = get_evaluation_status(eval_id)
    assert eval_data["status"] == "completed", f"Evaluation failed with status: {eval_data['status']}"
    
    # Check the output
    output = eval_data.get("output", "")
    
    # All tests should pass (network should be blocked)
    assert "PASS: Socket blocked" in output
    assert "PASS: HTTP blocked" in output
    assert "PASS: DNS blocked" in output
    
    # None should fail
    assert "FAIL:" not in output, "Network isolation test failed - network access was allowed"