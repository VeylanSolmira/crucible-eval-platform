"""
Executor configuration for image selection and resource limits.
"""

import os
from typing import Dict, Any

# Available executor images
EXECUTOR_IMAGES = {
    'default': os.getenv('EXECUTOR_IMAGE_DEFAULT', 'python:3.11-slim'),
    'base': os.getenv('EXECUTOR_IMAGE_BASE', 'executor-base:latest'),
    'ml': os.getenv('EXECUTOR_IMAGE_ML', 'executor-ml:latest'),
}

# Resource limits per image type
RESOURCE_LIMITS = {
    'default': {
        'memory': '512m',
        'cpus': '0.5',
        'tmpfs': {'/tmp': 'size=100m'},
    },
    'base': {
        'memory': '512m',
        'cpus': '0.5',
        'tmpfs': {'/tmp': 'size=100m'},
    },
    'ml': {
        'memory': '2g',  # More memory for ML workloads
        'cpus': '1.0',   # More CPU for model inference
        'tmpfs': {'/tmp': 'size=500m'},  # More temp space for model cache
    },
}

def get_executor_image(eval_type: str = 'default') -> str:
    """
    Get the appropriate executor image for the evaluation type.
    
    Args:
        eval_type: Type of evaluation (default, base, ml)
        
    Returns:
        Docker image name
    """
    return EXECUTOR_IMAGES.get(eval_type, EXECUTOR_IMAGES['default'])

def get_resource_limits(eval_type: str = 'default') -> Dict[str, Any]:
    """
    Get resource limits for the evaluation type.
    
    Args:
        eval_type: Type of evaluation (default, base, ml)
        
    Returns:
        Resource limits configuration
    """
    return RESOURCE_LIMITS.get(eval_type, RESOURCE_LIMITS['default'])

def get_container_config(eval_type: str = 'default') -> Dict[str, Any]:
    """
    Get complete container configuration for the evaluation type.
    
    Args:
        eval_type: Type of evaluation
        
    Returns:
        Container configuration dict
    """
    limits = get_resource_limits(eval_type)
    
    return {
        'image': get_executor_image(eval_type),
        'mem_limit': limits['memory'],
        'nano_cpus': int(float(limits['cpus'].rstrip()) * 1_000_000_000),
        'tmpfs': limits['tmpfs'],
        # Security settings remain the same for all types
        'network_mode': 'none',
        'read_only': True,
        'security_opt': ['no-new-privileges:true'],
        'user': 'executor' if eval_type != 'default' else None,  # Our images have executor user
    }