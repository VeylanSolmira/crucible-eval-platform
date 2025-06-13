"""
Security test scenarios - both safe demos and real attack patterns

WARNING: attack_scenarios.py contains real security attacks.
Only run these in isolated environments with proper sandboxing!
"""

from .safe_demo_scenarios import SAFE_DEMO_SCENARIOS
# Deliberately not importing attack_scenarios by default for safety

__all__ = ['SAFE_DEMO_SCENARIOS']
