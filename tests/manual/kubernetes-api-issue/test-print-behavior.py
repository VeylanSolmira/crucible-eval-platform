#!/usr/bin/env python3
"""Test if there's a difference in how Python handles the last expression"""

import subprocess

# Test 1: Code that ends with print
code1 = '''
import json
data = {'test': 'value'}
print(json.dumps(data))
'''

# Test 2: Code that has the dict as last expression
code2 = '''
import json
data = {'test': 'value'}
json.dumps(data)  # No print
data  # This is the last expression
'''

# Test 3: Code with trailing expression after print
code3 = '''
import json
data = {'test': 'value'}
print(json.dumps(data))
data  # Extra expression after print
'''

print("Test 1 - Normal print:")
result1 = subprocess.run(['python', '-c', code1], capture_output=True, text=True)
print(f"Output: {repr(result1.stdout)}")

print("\nTest 2 - No print, dict as last expression:")
result2 = subprocess.run(['python', '-c', code2], capture_output=True, text=True)
print(f"Output: {repr(result2.stdout)}")

print("\nTest 3 - Print followed by dict expression:")
result3 = subprocess.run(['python', '-c', code3], capture_output=True, text=True)
print(f"Output: {repr(result3.stdout)}")