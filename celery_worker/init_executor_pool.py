#!/usr/bin/env python3
"""
Initialize the executor pool in Redis.

This script sets up the available executors in Redis for the task chaining
implementation to use.
"""

import os
import json
import redis
import time

# Configuration
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
EXECUTOR_COUNT = int(os.environ.get("EXECUTOR_COUNT", "3"))
EXECUTOR_BASE_URL = os.environ.get("EXECUTOR_BASE_URL", "http://executor")

# Initialize Redis client
redis_client = redis.from_url(REDIS_URL)


def initialize_executor_pool():
    """Initialize the executor pool with available executors."""
    print(f"Initializing executor pool with {EXECUTOR_COUNT} executors...")
    
    # Clear existing pool
    redis_client.delete("executors:available")
    
    # Clear any busy markers
    busy_keys = list(redis_client.scan_iter(match="executor:busy:*"))
    if busy_keys:
        print(f"Clearing {len(busy_keys)} busy markers...")
        for key in busy_keys:
            redis_client.delete(key)
    
    # Add all executors as available
    executor_urls = [f"{EXECUTOR_BASE_URL}-{i+1}:8083" for i in range(EXECUTOR_COUNT)]
    
    for url in executor_urls:
        executor_data = {
            "url": url,
            "added_at": time.time()
        }
        redis_client.lpush("executors:available", json.dumps(executor_data))
        print(f"  Added: {url}")
    
    print(f"\n✅ Initialized pool with {len(executor_urls)} executors")
    
    # Verify
    available_count = redis_client.llen("executors:available")
    print(f"Verification: {available_count} executors in pool")


if __name__ == "__main__":
    initialize_executor_pool()