#!/usr/bin/env python3
"""
Demo evaluation code that properly tests network isolation.
This code will be executed inside Docker containers to verify isolation.
"""

import time
import random
import socket
import urllib.request

print("Advanced evaluation starting...")
time.sleep(random.uniform(1, 3))  # Simulate variable work

# Generate some results
result = sum(range(100))
print(f"Calculation result: {result}")

# Test network isolation properly
print("\nTesting network isolation:")

# Test 1: Import test (not sufficient!)
try:
    import requests  # noqa: F401
    print("⚠️  Note: requests module found (but may not work)")
except ImportError:
    print("ℹ️  Info: requests module not installed")

# Test 2: Actual network connection test
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    sock.connect(("8.8.8.8", 53))  # Try to connect to Google DNS
    sock.close()
    print("❌ FAIL: Network access allowed - connected to 8.8.8.8!")
except Exception as e:
    print(f"✅ PASS: Network blocked - {type(e).__name__}: {e}")

# Test 3: HTTP request test
try:
    response = urllib.request.urlopen("http://example.com", timeout=2)
    print(f"❌ FAIL: HTTP request succeeded - status {response.status}")
except Exception as e:
    print(f"✅ PASS: HTTP blocked - {type(e).__name__}")

# Test 4: DNS resolution test
try:
    ip = socket.gethostbyname("google.com")
    print(f"❌ FAIL: DNS resolution succeeded - google.com = {ip}")
except Exception as e:
    print(f"✅ PASS: DNS blocked - {type(e).__name__}")

print("\nEvaluation complete!")