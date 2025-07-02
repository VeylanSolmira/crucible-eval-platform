#!/usr/bin/env python3
"""
Standalone security demo runner
Safe to run in any environment - only performs read-only checks
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from security_scenarios.safe_demo_scenarios import SAFE_DEMO_SCENARIOS
from security_scenarios.security_runner import SecurityTestRunner
import security_scenarios.attack_scenarios


def main():
    print("🔒 Running Safe Security Demos")
    print("=" * 60)
    print("These demos show security concepts without performing attacks")
    print("Safe to run with subprocess, Docker, or gVisor")
    print("=" * 60)

    # Temporarily replace attack scenarios with safe demos
    original_scenarios = security_scenarios.attack_scenarios.ATTACK_SCENARIOS
    security_scenarios.attack_scenarios.ATTACK_SCENARIOS = SAFE_DEMO_SCENARIOS

    try:
        # Create runner with subprocess included (safe for demos)
        runner = SecurityTestRunner(include_subprocess=True)
        runner.run_all_scenarios()
    finally:
        # Restore original scenarios
        security_scenarios.attack_scenarios.ATTACK_SCENARIOS = original_scenarios


if __name__ == "__main__":
    main()
