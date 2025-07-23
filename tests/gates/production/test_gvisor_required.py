#!/usr/bin/env python3
"""Production environment requirement tests

These tests MUST pass in production environments.
They verify critical security requirements that cannot be compromised.
"""

import pytest
import subprocess
import os

def is_gvisor_available():
    """Check if gVisor runtime is available in the cluster"""
    try:
        result = subprocess.run(
            ["kubectl", "get", "runtimeclass", "gvisor"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False

@pytest.mark.production
@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("ENVIRONMENT", "").lower() == "development" and os.getenv("GVISOR_AVAILABLE", "true").lower() == "false",
    reason="gVisor disabled in development via GVISOR_AVAILABLE env var"
)
def test_gvisor_required():
    """Test that gVisor is available in production
    
    This is a hard requirement - production MUST have gVisor.
    """
    if not is_gvisor_available():
        pytest.fail(
            "CRITICAL SECURITY FAILURE: gVisor is not available!\n"
            "\n"
            "Production deployments MUST have gVisor installed for:\n"
            "- Kernel isolation from untrusted code\n"
            "- System call filtering\n"
            "- Protection against container escapes\n"
            "\n"
            "To fix:\n"
            "1. For GKE: Use --enable-sandbox flag\n"
            "2. For EKS: Deploy custom AMI with gVisor\n"
            "3. See: docs/security/gvisor-production-deployment.md"
        )


# Run production tests with: pytest -m production tests/