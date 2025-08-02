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

# Test 1: Try to read /etc/passwd (should be readable - normal Linux behavior)
try:
    with open('/etc/passwd', 'r') as f:
        content = f.read()
    results.append(f"PASS: Read /etc/passwd - {len(content)} bytes (normal behavior)")
except Exception as e:
    results.append(f"WARN: Cannot read /etc/passwd - {type(e).__name__} (unexpected)")

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

# Test 5: Robust gVisor detection
# gVisor blocks certain /proc files that are normally present
gvisor_blocked_files = ['/proc/kcore', '/proc/kallsyms', '/proc/modules']
missing_count = 0

for path in gvisor_blocked_files:
    if not os.path.exists(path):
        missing_count += 1

# If all gVisor-blocked files are missing, we're likely under gVisor
if missing_count == len(gvisor_blocked_files):
    results.append("INFO: Running under gVisor (detected via missing /proc files)")
else:
    results.append(f"INFO: Running under standard kernel ({missing_count}/{len(gvisor_blocked_files)} gVisor indicators)")

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
    
    # /etc/passwd should be readable (normal Linux behavior)
    assert "PASS: Read /etc/passwd" in output, \
        "/etc/passwd should be readable - this is normal Linux behavior"
    
    # Check for gVisor detection
    if GVISOR_AVAILABLE:
        # With gVisor: Should detect it via missing /proc files
        assert "Running under gVisor" in output, \
            "Should detect gVisor runtime via missing /proc files"
        print("\n✓ gVisor detected and working properly")
        print("  - Syscall filtering active (not file blocking)")
        print("  - Container still has normal filesystem access")
    else:
        # Without gVisor: Standard kernel
        if IS_PRODUCTION:
            # This shouldn't happen - we check above
            pytest.fail("Production requires gVisor")
        
        assert "Running under standard kernel" in output, \
            "Should detect standard kernel when gVisor is not present"
        
        # Development mode warning
        print("\n⚠️  WARNING: Running without gVisor")
        print("   - No syscall filtering")
        print("   - Production MUST use gVisor for security")
    
    # Always check for critical failures
    assert "FAIL: Cannot write to /tmp" not in output, "Should be able to write to /tmp"