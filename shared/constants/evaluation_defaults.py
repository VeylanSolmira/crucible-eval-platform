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

# Priority levels
PRIORITY_HIGH = 1
PRIORITY_NORMAL = 0
PRIORITY_LOW = -1