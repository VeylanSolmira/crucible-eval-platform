#!/usr/bin/env python3
"""Simple network test for execution engine verification"""

import socket
import urllib.request

print("Testing network isolation...")

# Test 1: Try actual network connection
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    sock.connect(("8.8.8.8", 53))  # Google DNS
    print("❌ Network access allowed - socket connected!")
    sock.close()
except Exception as e:
    print(f"✅ Network blocked - socket failed: {e}")

# Test 2: Try HTTP request
try:
    response = urllib.request.urlopen("http://example.com", timeout=2)
    print(f"❌ Network access allowed - HTTP {response.status}!")
except Exception as e:
    print(f"✅ Network blocked - HTTP failed: {e}")

# Test 3: Try DNS resolution
try:
    ip = socket.gethostbyname("google.com")
    print(f"❌ Network access allowed - DNS resolved to {ip}!")
except Exception as e:
    print(f"✅ Network blocked - DNS failed: {e}")

print("Network isolation test complete!")