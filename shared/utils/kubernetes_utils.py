"""
Kubernetes-related utility functions shared across services.
"""
import uuid
from typing import Optional


def generate_job_name(eval_id: str, suffix: Optional[str] = None) -> str:
    """
    Generate a Kubernetes-compliant job name from an evaluation ID.
    
    Kubernetes naming rules:
    - Must be lowercase alphanumeric characters or '-'
    - Must start and end with alphanumeric
    - Maximum 63 characters
    
    Args:
        eval_id: The evaluation ID to base the name on
        suffix: Optional suffix (if not provided, generates a UUID suffix)
    
    Returns:
        A Kubernetes-compliant job name
    """
    # Replace underscores with hyphens for K8s compliance
    eval_id_safe = eval_id.replace('_', '-').lower()
    
    # Truncate to leave room for prefix and suffix
    # "eval-" (5) + eval_id (20) + "-" (1) + suffix (8) = 34 chars total
    eval_id_safe = eval_id_safe[:20]
    
    # Generate suffix if not provided
    if suffix is None:
        suffix = uuid.uuid4().hex[:8]
    
    return f"{eval_id_safe}-{suffix}"


def extract_eval_id_from_job_name(job_name: str) -> Optional[str]:
    """
    Extract the evaluation ID from a job name.
    
    Note: This returns the safe version (with hyphens instead of underscores).
    The original eval_id cannot be perfectly reconstructed if it had underscores.
    
    Args:
        job_name: The Kubernetes job name
    
    Returns:
        The evaluation ID portion of the job name, or None if not a valid eval job name
    """
    # No prefix to remove anymore
    remainder = job_name
    
    # Split by last hyphen to remove UUID suffix
    parts = remainder.rsplit('-', 1)
    if len(parts) != 2:
        return None
    
    return parts[0]


def get_job_name_prefix(eval_id: str) -> str:
    """
    Get the job name prefix for matching jobs by evaluation ID.
    
    This is useful for finding all jobs related to an evaluation.
    
    Args:
        eval_id: The evaluation ID
    
    Returns:
        The prefix to match job names
    """
    eval_id_safe = eval_id.replace('_', '-').lower()[:20]
    return f"{eval_id_safe}-"