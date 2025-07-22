#!/usr/bin/env python3
"""
Run minimal smoke tests to verify cluster access before running main test suite.

Usage:
    python tests/smoke/run_smoke_tests.py
    
Exit codes:
    0 - All smoke tests passed, ready for main tests
    1 - Smoke tests failed, cluster not ready
    2 - Missing dependencies (kubectl, etc.)
"""

import sys
import subprocess
import shutil
import os


def check_prerequisites():
    """Check if required tools are installed."""
    tools = {
        "kubectl": "kubectl is required for Kubernetes access",
        "python": "Python is required",
    }
    
    missing = []
    for tool, message in tools.items():
        if not shutil.which(tool):
            missing.append(f"  ✗ {message}")
    
    if missing:
        print("Missing prerequisites:")
        print("\n".join(missing))
        return False
    
    print("✓ All prerequisites found")
    return True


def main():
    """Run smoke tests and report results."""
    print("Kubernetes Cluster Access Smoke Tests")
    print("=" * 60)
    print()
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(2)
    
    print("\nRunning smoke tests...")
    print("-" * 60)
    
    # Run the smoke tests
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_file = os.path.join(script_dir, "test_cluster_access.py")
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, 
         "-v", "--tb=short", "--no-header"],
    )
    
    print("\n" + "=" * 60)
    
    if result.returncode == 0:
        print("✅ SMOKE TESTS PASSED")
        print("\nCluster is ready for main test suite!")
        print("\nNext steps:")
        print("1. Run full test suite inside cluster: python tests/run_tests.py")
        print("2. Or run specific test suites: python tests/run_tests.py integration")
        sys.exit(0)
    else:
        print("❌ SMOKE TESTS FAILED")
        print("\nCluster is not ready. Please check:")
        print("1. kubectl is configured correctly")
        print("2. The target namespace exists")
        print("3. All required services are deployed")
        print("4. Pods are in Running state")
        sys.exit(1)


if __name__ == "__main__":
    main()