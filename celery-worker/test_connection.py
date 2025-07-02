#!/usr/bin/env python3
"""Test Celery connection to Redis"""

import os
import sys
from celery import Celery

# Test direct Redis connection first
try:
    import redis

    broker_url = os.environ.get("CELERY_BROKER_URL", "redis://celery-redis:6379/0")
    print(f"Testing Redis connection to: {broker_url}")

    r = redis.Redis.from_url(broker_url)
    print(f"Redis ping: {r.ping()}")
    print("✓ Redis connection successful")
except Exception as e:
    print(f"✗ Redis connection failed: {e}")
    sys.exit(1)

# Test Celery connection
try:
    print("\nTesting Celery connection...")
    app = Celery("test", broker=broker_url)

    # Try to inspect the broker
    inspect = app.control.inspect()
    stats = inspect.stats()

    if stats:
        print(f"✓ Celery connection successful. Found {len(stats)} workers")
    else:
        print("✓ Celery connection successful (no workers found yet)")

except Exception as e:
    print(f"✗ Celery connection failed: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
