#!/usr/bin/env python3
"""Large output test - generates lots of output to test handling"""

print("Testing large output handling...")

# Generate lots of output
for i in range(1000):
    print(f"Line {i}: " + "x" * 100)

print("\nGenerated 1000 lines of output!")