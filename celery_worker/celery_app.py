"""
Celery application instance.

This module creates and configures the Celery app instance separately from tasks,
allowing for cleaner imports and better testability.
"""

from celery import Celery

# Create the Celery app instance
app = Celery("crucible_worker")

# Load configuration from celeryconfig module
app.config_from_object("celery_worker.celeryconfig")

# Auto-discover tasks in the celery_worker package
app.autodiscover_tasks(["celery_worker"])