#!/usr/bin/env python3
"""Test if newline escaping affects output"""

import subprocess

# Test with actual newlines
code1 = """
import json
data = {'test': 'value'}
print(json.dumps(data))
"""

# Test with escaped newlines (like in K8s YAML)
code2 = "\\nimport json\\ndata = {'test': 'value'}\\nprint(json.dumps(data))\\n"

print("Test 1 - Actual newlines:")
result1 = subprocess.run(['python', '-c', code1], capture_output=True, text=True)
print(f"Output: {repr(result1.stdout)}")

print("\nTest 2 - Escaped newlines:")
result2 = subprocess.run(['python', '-c', code2], capture_output=True, text=True)
print(f"Output: {repr(result2.stdout)}")

# Test if the issue is with how Python interprets the final_data variable
code3 = """
import json
results = {"available": ["test"], "unavailable": []}
final_data = {
    "available": results["available"],
    "unavailable": results["unavailable"]
}
print(json.dumps(final_data))
"""

print("\nTest 3 - Dict construction like in test:")
result3 = subprocess.run(['python', '-c', code3], capture_output=True, text=True)
print(f"Output: {repr(result3.stdout)}")