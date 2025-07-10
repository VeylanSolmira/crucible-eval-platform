#!/usr/bin/env python3
"""Memory exhaustion demo - attempts to exceed memory limits"""

import sys

print("Memory Exhaustion Test")
print("=" * 40)
print("Container memory limit: 512MB")
print("This script will attempt to exceed the limit")
print()

# Test 1: Memory allocation
print("Test 1: Memory allocation")
print("Attempting to allocate 500MB...")
try:
    # Allocate ~500MB (list of 125 million integers)
    big_list = [i for i in range(125_000_000)]
    print(f"✓ Successfully allocated {len(big_list):,} integers")
    print(f"  Approximate size: {sys.getsizeof(big_list) / 1024 / 1024:.1f} MB")
except MemoryError:
    print("✗ MemoryError: Allocation failed (resource limit reached)")

print()

# Test 2: Attempting larger allocation
print("Test 2: Excessive memory allocation")
print("Attempting to allocate 2GB...")
try:
    # Try to allocate ~2GB
    huge_list = [0] * (500_000_000)
    print("✓ Successfully allocated (this shouldn't happen!)")
except MemoryError:
    print("✗ MemoryError: Platform memory limits enforced")
    print("  This is expected behavior - protecting system resources")

print()

# Note about what to expect
print("Expected outcome:")
print("- The 500MB allocation should succeed")
print("- The 2GB allocation will cause the container to be killed")
print("- You should see 'Memory limit exceeded (512MB)' with proper exit code handling")
print("\nIf the container is killed, logs may be lost (known limitation)")