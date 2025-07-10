#!/usr/bin/env python3
"""Timeout demonstration - shows 30-second execution limit"""

print("Starting infinite loop...")
print("This will timeout after 30 seconds")
print("You should see this get terminated")

import time
count = 0
while True:
    # Print progress every 5 seconds so we can see it working
    if count % 5 == 0:
        print(f"Still running... {count} seconds elapsed")
    time.sleep(1)
    count += 1