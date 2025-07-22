#!/usr/bin/env python3
"""Test different ways of passing code to Python"""

import subprocess
import json

test_code = '''
import json
data = {"test": "value", "list": [1, 2, 3]}
final = {"result": data}
print(json.dumps(final))
'''

print("Test 1 - Command as list (like manual YAML):")
result1 = subprocess.run(["python", "-c", test_code], capture_output=True, text=True)
print(f"Output: {repr(result1.stdout)}")
print(f"Stderr: {repr(result1.stderr)}")

print("\nTest 2 - Command as single string:")
result2 = subprocess.run(f"python -c '{test_code}'", shell=True, capture_output=True, text=True)
print(f"Output: {repr(result2.stdout)}")
print(f"Stderr: {repr(result2.stderr)}")

# Test if escaping matters
test_code_escaped = test_code.replace('"', '\\"')
print("\nTest 3 - With escaped quotes:")
result3 = subprocess.run(["python", "-c", test_code_escaped], capture_output=True, text=True)
print(f"Output: {repr(result3.stdout)}")
print(f"Stderr: {repr(result3.stderr)}")