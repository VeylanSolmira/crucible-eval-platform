"""
Resource parsing utilities for Kubernetes resource specifications.

This module provides functions to parse memory and CPU resource strings
into standard units (MB for memory, millicores for CPU).
"""


def parse_memory(memory_str: str) -> int:
    """
    Parse memory string to MB.
    
    Supports formats like:
    - 512Mi (mebibytes)
    - 1Gi (gibibytes)
    - 1024Ki (kibibytes)
    - 1073741824 (bytes)
    
    Args:
        memory_str: Memory specification string
        
    Returns:
        Memory in megabytes (MB)
    """
    if memory_str.endswith("Ti"):
        return int(float(memory_str[:-2]) * 1024 * 1024)
    elif memory_str.endswith("Gi"):
        return int(float(memory_str[:-2]) * 1024)
    elif memory_str.endswith("Mi"):
        return int(memory_str[:-2])
    elif memory_str.endswith("Ki"):
        return int(float(memory_str[:-2]) / 1024)
    else:
        # Assume bytes
        return int(int(memory_str) / 1024 / 1024)


def parse_cpu(cpu_str: str) -> int:
    """
    Parse CPU string to millicores.
    
    Supports formats like:
    - 100m (millicores)
    - 0.1 (cores)
    - 2 (cores)
    
    Args:
        cpu_str: CPU specification string
        
    Returns:
        CPU in millicores
    """
    if cpu_str.endswith("m"):
        return int(cpu_str[:-1])
    else:
        # Assume cores
        return int(float(cpu_str) * 1000)