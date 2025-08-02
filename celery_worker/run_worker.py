#!/usr/bin/env python
"""
Entry point for running the Celery worker with embedded health check server.

This provides HTTP health endpoints for Kubernetes probes while keeping
everything in a single process for accurate health reporting.
"""

import os
import sys
import asyncio
import threading
from celery_worker.celery_app import app
from celery_worker.health_server import run_health_server


def start_health_server_thread():
    """Start health server in a background thread."""
    broker_url = os.environ.get("CELERY_BROKER_URL", "redis://celery-redis:6379/0")
    port = int(os.environ.get("HEALTH_PORT", "8088"))
    
    def run_in_thread():
        asyncio.run(run_health_server(broker_url, port))
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
    print(f"Health server started on port {port}")


if __name__ == "__main__":
    # Start health server in background thread
    start_health_server_thread()
    
    # Start celery worker directly using worker_main
    # This avoids CLI argument parsing issues
    argv = [
        'worker',
        '--loglevel=info',
        f'--concurrency={os.environ.get("CELERY_CONCURRENCY", "2")}',
        '-Q', 'high_priority,evaluation,batch,maintenance'
    ]
    app.worker_main(argv)