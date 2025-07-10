#!/usr/bin/env python3
"""CPU exhaustion demo - attempts to use excessive CPU resources"""

import multiprocessing
import time

print("CPU Exhaustion Test")
print("=" * 40)
print("Attempting to spawn multiple CPU-intensive processes...")
print(f"System has {multiprocessing.cpu_count()} CPU cores")
print("Container is limited to 0.5 CPU cores")
print()

def cpu_burn():
    """Burn CPU cycles indefinitely"""
    while True:
        # Intentionally wasteful computation
        _ = sum(i * i for i in range(10000))

# Try to spawn many processes to overwhelm CPU limits
processes = []
try:
    # Try to create 10 processes (way more than our 0.5 CPU limit)
    for i in range(10):
        print(f"Starting CPU-intensive process {i+1}...")
        p = multiprocessing.Process(target=cpu_burn)
        p.start()
        processes.append(p)
        time.sleep(0.1)  # Brief pause to see output
    
    print(f"\nSpawned {len(processes)} processes")
    print("Monitoring CPU usage for 10 seconds...")
    
    # Let them run for a bit to show CPU throttling
    start_time = time.time()
    while time.time() - start_time < 10:
        elapsed = time.time() - start_time
        print(f"[{elapsed:4.1f}s] Processes running (CPU should be throttled to 50%)...")
        time.sleep(2)
    
    print("\nCPU limit successfully enforced - processes throttled, not killed")
    
except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {e}")
    
finally:
    # Clean up
    print("\nCleaning up processes...")
    for p in processes:
        p.terminate()
    for p in processes:
        p.join(timeout=1)
    print("✅ Cleanup complete")