"""
Priority mapping for evaluation pods.

Maps numeric priority values to Kubernetes PriorityClass names and Celery queues.
"""

# Define priority ranges and their corresponding PriorityClass names
PRIORITY_CLASS_MAPPING = [
    # (min_priority, max_priority, priority_class_name)
    (2000, float('inf'), 'critical-priority'),           # 2000+ -> Critical services
    (1000, 1999, 'high-priority-evaluation'),           # 1000-1999 -> High priority production
    (500, 999, 'normal-priority-evaluation'),           # 500-999 -> Normal priority production  
    (400, 499, 'test-infrastructure-priority'),         # 400-499 -> Test infrastructure
    (350, 399, 'test-high-priority-evaluation'),        # 350-399 -> High priority test
    (250, 349, 'test-normal-priority-evaluation'),      # 250-349 -> Normal priority test
    (150, 249, 'test-low-priority-evaluation'),         # 150-249 -> Low priority test
    (100, 149, 'low-priority-evaluation'),              # 100-149 -> Low priority production
    (0, 99, 'low-priority-evaluation'),                 # 0-99 -> Very low priority
]

def get_priority_class(priority: int) -> str:
    """
    Map numeric priority to Kubernetes PriorityClass name.
    
    Args:
        priority: Numeric priority value
        
    Returns:
        Name of the PriorityClass to use
    """
    for min_pri, max_pri, class_name in PRIORITY_CLASS_MAPPING:
        if min_pri <= priority <= max_pri:
            return class_name
    
    # Default to low priority if no match
    return 'low-priority-evaluation'


def get_celery_queue(priority: int) -> str:
    """
    Map numeric priority to Celery queue name.
    
    Args:
        priority: Numeric priority value
        
    Returns:
        Name of the Celery queue to use
    """
    if priority >= 1000:
        return 'high_priority'
    elif priority >= 250:
        return 'evaluation'  # Normal/medium priority
    else:
        return 'low_priority'


# For backward compatibility, map old -1/0/1 values
LEGACY_PRIORITY_MAPPING = {
    -1: 150,  # Test low priority
    0: 250,   # Test normal priority  
    1: 350,   # Test high priority
}

def normalize_priority(priority: int) -> int:
    """
    Convert legacy priority values to new numeric system.
    
    Args:
        priority: Priority value (could be legacy -1/0/1 or new numeric)
        
    Returns:
        Normalized numeric priority
    """
    # If it's a legacy value, map it
    if -1 <= priority <= 1:
        return LEGACY_PRIORITY_MAPPING.get(priority, 250)
    
    # Otherwise use as-is
    return priority