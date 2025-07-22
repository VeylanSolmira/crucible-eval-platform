#!/usr/bin/env python
"""
Entry point for running the Celery worker.

This allows us to run the worker with proper package context.
"""

import sys
from celery_worker.celery_app import app

if __name__ == "__main__":
    # Use app.start() which handles argv properly
    app.start()