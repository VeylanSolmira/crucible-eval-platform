"""
Default resource limits for evaluations.

This module provides the single source of truth for evaluation resource defaults
used across the platform (API, dispatcher, tests, etc.).
"""

# Default resource limits for evaluations
# These match the defaultRequest values in k8s/base/security/resource-quotas.yaml
DEFAULT_MEMORY_LIMIT = "128Mi"
DEFAULT_CPU_LIMIT = "100m"

# Parsed values for use in calculations
DEFAULT_MEMORY_MB = 128  # 128 MiB
DEFAULT_CPU_MILLICORES = 100  # 0.1 CPU core

# Maximum allowed resources per evaluation
MAX_MEMORY_LIMIT = "512Mi"
MAX_CPU_LIMIT = "500m"

# Timeout defaults
DEFAULT_TIMEOUT_SECONDS = 300  # 5 minutes
MAX_TIMEOUT_SECONDS = 600  # 10 minutes

# Legacy priority levels (deprecated - use PriorityClass enum)
PRIORITY_HIGH = 1
PRIORITY_NORMAL = 0
PRIORITY_LOW = -1

# New priority system using Kubernetes priority values
from enum import IntEnum

class PriorityClass(IntEnum):
    """Kubernetes priority class values for evaluation pods."""
    # Production priorities
    CRITICAL = 2000                    # Critical services only
    HIGH_PRIORITY_EVAL = 1000         # High priority production evaluations
    NORMAL_PRIORITY_EVAL = 500        # Normal priority production evaluations
    LOW_PRIORITY_EVAL = 100           # Low priority production evaluations
    
    # Test infrastructure and evaluations
    TEST_INFRASTRUCTURE = 400         # Test runners and coordinators
    TEST_HIGH_PRIORITY_EVAL = 350     # High priority test evaluations
    TEST_NORMAL_PRIORITY_EVAL = 250   # Normal priority test evaluations  
    TEST_LOW_PRIORITY_EVAL = 150      # Low priority test evaluations (default for tests)