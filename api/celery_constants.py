"""
Constants and configuration values for the API service.
"""

# Task mapping TTL - how long to keep the eval_id <-> task_id mapping
# This should be longer than the maximum expected evaluation duration
TASK_MAPPING_TTL_SECONDS = 86400  # 24 hours

# Future considerations for longer evaluations:
# - For multi-day evaluations, increase to 604800 (7 days)
# - Consider refreshing TTL when task status is checked
# - May need persistent storage (database) for very long evaluations