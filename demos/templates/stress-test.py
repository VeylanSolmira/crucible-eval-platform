#!/usr/bin/env python3
"""Stress test - simulates variable workload for concurrent testing"""

import random
import time

# Simulate variable workload
sleep_time = random.uniform(1, 3)
print(f"Evaluation {random.randint(1000, 9999)} starting...")
print(f"Will process for {sleep_time:.1f} seconds")

time.sleep(sleep_time)

# Generate some results
result = sum(range(random.randint(100, 1000)))
print(f"Completed! Result: {result}")