#!/usr/bin/env python3
"""Integration tests for filesystem isolation in containers"""

import pytest
import requests
import time
from tests.utils import submit_evaluation, wait_for_completion, get_evaluation_status

FILESYSTEM_TEST_CODE = '''
import os

results = []

# Test 1: Try to read sensitive file
try:
    with open('/etc/passwd', 'r') as f:
        content = f.read()
    results.append(f"FAIL: Read /etc/passwd - {len(content)} bytes")
except Exception as e:
    results.append(f"PASS: Cannot read /etc/passwd - {type(e).__name__}")

# Test 2: Try to write to /tmp (should work)
try:
    with open('/tmp/test.txt', 'w') as f:
        f.write("test")
    results.append("PASS: Can write to /tmp")
except Exception as e:
    results.append(f"FAIL: Cannot write to /tmp - {type(e).__name__}")

# Test 3: Try to write to root (should fail due to read-only)
try:
    with open('/test.txt', 'w') as f:
        f.write("test")
    results.append("FAIL: Can write to root directory")
except Exception as e:
    results.append(f"PASS: Cannot write to root - {type(e).__name__}")

# Test 4: List root directory (should work but limited)
try:
    files = os.listdir('/')
    results.append(f"INFO: Can list / - {len(files)} entries")
except Exception as e:
    results.append(f"FAIL: Cannot list / - {type(e).__name__}")

for result in results:
    print(result)
'''

@pytest.mark.integration
def test_filesystem_isolation():
    """Test that containers have proper filesystem restrictions"""
    # Submit the filesystem test code
    eval_id = submit_evaluation(FILESYSTEM_TEST_CODE)
    assert eval_id is not None, "Failed to submit evaluation"
    
    # Wait for completion
    status = wait_for_completion(eval_id, timeout=30)
    assert status is not None, "Evaluation did not complete in time"
    
    # Get the full evaluation details
    eval_data = get_evaluation_status(eval_id)
    assert eval_data["status"] == "completed", f"Evaluation failed with status: {eval_data['status']}"
    
    # Check the output
    output = eval_data.get("output", "")
    
    # Check expected behaviors
    assert "PASS: Cannot read /etc/passwd" in output, "Should not be able to read /etc/passwd"
    assert "PASS: Can write to /tmp" in output, "Should be able to write to /tmp"
    assert "PASS: Cannot write to root" in output, "Should not be able to write to root"
    
    # Check for unexpected failures
    assert "FAIL: Cannot write to /tmp" not in output, "Should be able to write to /tmp"
    assert "FAIL: Read /etc/passwd" not in output, "Should not be able to read sensitive files"