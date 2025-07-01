#!/usr/bin/env python3
"""Test Celery integration"""
from celery import Celery

# Create Celery app with same config as worker
app = Celery('test', broker='redis://localhost:6380/0')

# Test 1: Check if we can connect
try:
    # Get worker stats
    stats = app.control.inspect().stats()
    if stats:
        print("✅ Connected to Celery broker")
        print(f"✅ Found {len(stats)} worker(s)")
        for worker, info in stats.items():
            print(f"   - {worker}")
    else:
        print("❌ No workers found")
except Exception as e:
    print(f"❌ Connection failed: {e}")

# Test 2: Submit a health check task
try:
    result = app.send_task('tasks.health_check')
    print(f"✅ Submitted health check task: {result.id}")
    
    # Wait for result (max 5 seconds)
    health = result.get(timeout=5)
    print(f"✅ Health check result: {health}")
except Exception as e:
    print(f"❌ Task submission failed: {e}")

# Test 3: Check task queues
try:
    queues = app.control.inspect().active_queues()
    if queues:
        print("✅ Active queues:")
        for worker, worker_queues in queues.items():
            for q in worker_queues:
                print(f"   - {q['name']}")
except Exception as e:
    print(f"❌ Queue inspection failed: {e}")