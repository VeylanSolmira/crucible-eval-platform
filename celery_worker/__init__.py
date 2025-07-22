"""Celery Worker - Task queue worker for evaluation jobs."""

# Export the Celery app instance
from celery_worker.celery_app import app

__all__ = ["app"]