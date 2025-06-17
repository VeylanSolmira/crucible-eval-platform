#!/usr/bin/env python3
"""Test script to verify container connectivity"""

import subprocess
import time
import requests

print("🔍 Checking Docker container status...")

# Check if container is running
result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
if 'crucible-platform' in result.stdout:
    print("✅ Container is running")
else:
    print("❌ Container not found. Starting it...")
    subprocess.run(['docker', 'compose', 'up', '-d'])
    time.sleep(5)

# Test connection
print("\n🔍 Testing connection to http://localhost:8080...")
try:
    response = requests.get('http://localhost:8080', timeout=5)
    print(f"✅ Connection successful! Status: {response.status_code}")
    print(f"   Response length: {len(response.text)} bytes")
except requests.exceptions.ConnectionError:
    print("❌ Connection refused - server not accessible")
    print("\n🔍 Checking what's listening on port 8080...")
    subprocess.run(['lsof', '-i', ':8080'])
except requests.exceptions.Timeout:
    print("❌ Connection timeout - server not responding")

# Check container logs
print("\n🔍 Recent container logs:")
subprocess.run(['docker', 'logs', 'crucible-platform', '--tail', '10'])

# Get container IP
print("\n🔍 Container network info:")
result = subprocess.run(['docker', 'inspect', 'crucible-platform', '--format', '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'], capture_output=True, text=True)
container_ip = result.stdout.strip()
if container_ip:
    print(f"   Container IP: {container_ip}")
    print(f"   Try: curl http://{container_ip}:8080")