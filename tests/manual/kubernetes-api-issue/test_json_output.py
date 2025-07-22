#!/usr/bin/env python3
"""Test why JSON output is being converted to dict repr"""

import subprocess
import json

# Test 1: Direct execution
print("Test 1: Direct execution")
code1 = """
import json
data = {'test': 'value'}
print(json.dumps(data))
"""
result1 = subprocess.run(['python', '-c', code1], capture_output=True, text=True)
print(f"Output: {repr(result1.stdout)}")
print(f"Is valid JSON: {result1.stdout.strip()}")

# Test 2: With the exact code structure from the test
print("\nTest 2: With exact test structure")
code2 = """
import json as json_module
final_data = {
    "available": ["numpy", "pandas"],
    "tests": ["Hash test: abc...", "Date test: 2025"]
}
print(json_module.dumps(final_data, indent=2))
"""
result2 = subprocess.run(['python', '-c', code2], capture_output=True, text=True)
print(f"Output: {repr(result2.stdout)}")
print(f"First 50 chars: {repr(result2.stdout[:50])}")

# Test 3: Check if there's any implicit conversion
print("\nTest 3: Check for implicit conversion")
code3 = """
final_data = {'available': ['numpy'], 'tests': ['test1']}
final_data
"""
result3 = subprocess.run(['python', '-c', code3], capture_output=True, text=True)
print(f"Output: {repr(result3.stdout)}")
print(f"Length: {len(result3.stdout)}")