"""
Celery configuration for the evaluation worker.

This configuration supports both development and production environments
with sensible defaults and security best practices.
"""

import os
from kombu import Queue, Exchange

# Broker settings
broker_url = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

# Task settings
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]  # Security: Only accept JSON
timezone = "UTC"
enable_utc = True

# Task execution settings
task_track_started = True
task_time_limit = 600  # 10 minutes hard limit
task_soft_time_limit = 300  # 5 minutes soft limit
task_acks_late = True  # Task acknowledged after completion
worker_prefetch_multiplier = 1  # One task at a time per worker process
# Note: With concurrency=3 and prefetch=1, up to 3 tasks can be "claimed" by this worker
# This matches our executor count, preventing over-provisioning

# Result backend settings
result_expires = 3600  # Results expire after 1 hour
result_persistent = True  # Persist results across restarts

# Queue configuration
default_exchange = Exchange("crucible", type="direct")

task_queues = (
    Queue("evaluation", default_exchange, routing_key="evaluation", priority=5),
    Queue("high_priority", default_exchange, routing_key="high_priority", priority=10),
    Queue("batch", default_exchange, routing_key="batch", priority=1),
    Queue("maintenance", default_exchange, routing_key="maintenance", priority=0),
)

# Default queue
task_default_queue = "evaluation"
task_default_exchange = "crucible"
task_default_routing_key = "evaluation"

# Task routing
task_routes = {
    "celery_worker.tasks.assign_executor": {"queue": "evaluation"},
    "celery_worker.tasks.evaluate_code": {"queue": "evaluation"},
    "celery_worker.tasks.release_executor_task": {"queue": "evaluation"},
    "celery_worker.tasks.evaluate_code_high_priority": {"queue": "high_priority"},
    "celery_worker.tasks.batch_evaluation": {"queue": "batch"},
    "celery_worker.tasks.cleanup_old_evaluations": {"queue": "maintenance"},
}

# Worker settings
worker_max_tasks_per_child = 100  # Restart worker after 100 tasks (memory leaks)
worker_disable_rate_limits = False
worker_concurrency = int(os.environ.get("CELERY_CONCURRENCY", 4))

# Beat schedule (for scheduled tasks)
beat_schedule = {
    "cleanup-old-evaluations": {
        "task": "celery_worker.tasks.cleanup_old_evaluations",
        "schedule": 3600.0,  # Every hour
        "options": {"queue": "maintenance"},
    },
}

# Monitoring
worker_send_task_events = True
task_send_sent_event = True

# Security
worker_hijack_root_logger = False
worker_log_format = "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
worker_task_log_format = (
    "[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s"
)

# Development settings (override in production)
if os.environ.get("CELERY_DEVELOPMENT", "false").lower() == "true":
    task_always_eager = False  # Set True for synchronous execution in tests
    task_eager_propagates = True
    worker_log_color = True

# Redis connection pool settings
broker_connection_retry_on_startup = True
broker_connection_retry = True
broker_connection_max_retries = 10
broker_pool_limit = 10
broker_transport_options = {
    "visibility_timeout": 3600,  # 1 hour
    "fanout_prefix": True,
    "fanout_patterns": True,
    "socket_keepalive": True,
    "socket_connect_timeout": 30,
    "retry_on_timeout": True,
    "max_retries": 3,
    # Note: Redis doesn't support native priority queues like RabbitMQ
    # We use separate queues (high_priority, evaluation) instead
}
