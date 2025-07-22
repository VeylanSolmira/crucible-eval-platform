#!/usr/bin/env python3
"""Integration tests for filesystem isolation in containers"""

import pytest
import requests
import time
import subprocess
import os
from tests.utils.utils import submit_evaluation, wait_for_completion, get_evaluation_status

def is_gvisor_available():
    """Check if gVisor runtime is available in the cluster"""
    try:
        # Check if gVisor RuntimeClass exists
        result = subprocess.run(
            ["kubectl", "get", "runtimeclass", "gvisor"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False

# Check gVisor availability once at module level
GVISOR_AVAILABLE = is_gvisor_available()

# Check if we're in production (multiple ways to detect)
IS_PRODUCTION = any([
    os.getenv("ENVIRONMENT") == "production",
    os.getenv("REQUIRE_GVISOR", "false").lower() == "true",
    os.getenv("K8S_CLUSTER_TYPE") == "production"
])

FILESYSTEM_TEST_CODE = '''
import os

results = []

# Test 1: Try to read /etc/passwd (blocked by gVisor, readable without)
try:
    with open('/etc/passwd', 'r') as f:
        content = f.read()
    results.append(f"FAIL: Read /etc/passwd - {len(content)} bytes")
except Exception as e:
    results.append(f"PASS: Cannot read /etc/passwd - {type(e).__name__}")

# Test 2: Try to read /etc/shadow (should always fail - even without gVisor)
try:
    with open('/etc/shadow', 'r') as f:
        content = f.read()
    results.append(f"FAIL: Read /etc/shadow - {len(content)} bytes")
except Exception as e:
    results.append(f"PASS: Cannot read /etc/shadow - {type(e).__name__}")

# Test 3: Try to write to /tmp (should work)
try:
    with open('/tmp/test.txt', 'w') as f:
        f.write("test")
    results.append("PASS: Can write to /tmp")
except Exception as e:
    results.append(f"FAIL: Cannot write to /tmp - {type(e).__name__}")

# Test 4: Try to write to root (should fail due to read-only)
try:
    with open('/test.txt', 'w') as f:
        f.write("test")
    results.append("FAIL: Can write to root directory")
except Exception as e:
    results.append(f"PASS: Cannot write to root - {type(e).__name__}")

# Test 5: Check kernel info to detect gVisor
try:
    with open('/proc/version', 'r') as f:
        kernel = f.read().strip()
    if 'gVisor' in kernel:
        results.append("INFO: Running under gVisor kernel")
    else:
        results.append(f"INFO: Running under standard kernel")
except Exception as e:
    results.append(f"INFO: Cannot read kernel version - {type(e).__name__}")

for result in results:
    print(result)
'''

@pytest.mark.graybox
@pytest.mark.integration
def test_filesystem_isolation():
    """Test that containers have proper filesystem restrictions
    
    This test adapts based on runtime environment:
    - Production: REQUIRES gVisor (test fails if not available)
    - Development: Works with or without gVisor (different expectations)
    """
    # Production requirement: gVisor MUST be available
    if IS_PRODUCTION and not GVISOR_AVAILABLE:
        pytest.fail(
            "CRITICAL: Production environment detected but gVisor is not available!\n"
            "Production deployments MUST have gVisor for security.\n"
            "See: docs/security/gvisor-production-deployment.md"
        )
    
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
    
    # Common security requirements (work with or without gVisor)
    assert "PASS: Cannot read /etc/shadow" in output or "Cannot read /etc/shadow" in output, \
        "Should not be able to read /etc/shadow"
    assert "PASS: Can write to /tmp" in output, "Should be able to write to /tmp"
    assert "PASS: Cannot write to root" in output, "Should not be able to write to root"
    
    # Conditional expectations based on gVisor availability
    if GVISOR_AVAILABLE:
        # With gVisor: Full isolation expected
        assert "PASS: Cannot read /etc/passwd" in output, \
            "With gVisor, should not be able to read /etc/passwd"
        assert "FAIL: Read /etc/passwd" not in output, \
            "Should not be able to read sensitive files with gVisor"
    else:
        # Without gVisor: Limited isolation (development only)
        if IS_PRODUCTION:
            # This shouldn't happen - we check above
            pytest.fail("Production requires gVisor")
        
        # In development, /etc/passwd will be readable
        if "PASS: Cannot read /etc/passwd" in output:
            pytest.skip(
                "Test shows /etc/passwd is not readable - this might indicate:\n"
                "1. gVisor is actually working (good!)\n"
                "2. The evaluation failed to run properly\n"
                "Skipping as we can't determine which case this is."
            )
        
        # Development mode warning
        print("\n⚠️  WARNING: Running without gVisor - limited filesystem isolation")
        print("   - /etc/passwd is readable (expected in development)")
        print("   - Production MUST use gVisor for security")
    
    # Always check for critical failures
    assert "FAIL: Cannot write to /tmp" not in output, "Should be able to write to /tmp"