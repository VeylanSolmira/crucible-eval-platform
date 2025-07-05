#!/usr/bin/env python3
"""
Demo scenarios for the Crucible platform.
These demonstrate various capabilities and failure modes.
"""

# Demo 1: Basic successful evaluation
DEMO_HELLO_WORLD = """
print("Hello from Crucible!")
print("This evaluation is running in a secure container")

# Do some computation
result = sum(range(100))
print(f"Sum of 0-99: {result}")
"""

# Demo 2: Timeout demonstration
DEMO_TIMEOUT = """
print("Starting infinite loop...")
print("This will timeout after 30 seconds")

while True:
    # Infinite loop - will be killed by timeout
    pass
"""

# Demo 3: Syntax error handling
DEMO_SYNTAX_ERROR = """
print("This code has a syntax error")
if True
    print("Missing colon above!")
"""

# Demo 4: Runtime error handling
DEMO_RUNTIME_ERROR = """
print("This will cause a runtime error")
x = 1 / 0  # Division by zero
print("This line will never execute")
"""

# Demo 5: Network isolation test
DEMO_NETWORK_ISOLATION = """
import socket
import urllib.request

print("Testing network isolation...")

# Test 1: Direct socket connection
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    sock.connect(("8.8.8.8", 53))  # Google DNS
    sock.close()
    print("❌ FAIL: Network access allowed!")
except Exception as e:
    print(f"✅ PASS: Network blocked - {type(e).__name__}")

# Test 2: HTTP request
try:
    response = urllib.request.urlopen("http://example.com", timeout=2)
    print(f"❌ FAIL: HTTP request succeeded!")
except Exception as e:
    print(f"✅ PASS: HTTP blocked - {type(e).__name__}")

# Test 3: DNS resolution
try:
    ip = socket.gethostbyname("google.com")
    print(f"❌ FAIL: DNS resolution succeeded!")
except Exception as e:
    print(f"✅ PASS: DNS blocked - {type(e).__name__}")

print("\\nNetwork isolation test complete!")
"""

# Demo 6: File system isolation
DEMO_FILESYSTEM_ISOLATION = """
import os

print("Testing file system isolation...")

# Test 1: Try to read sensitive file
try:
    with open('/etc/passwd', 'r') as f:
        content = f.read()
    print(f"❌ FAIL: Read /etc/passwd - {len(content)} bytes")
except Exception as e:
    print(f"✅ PASS: Cannot read /etc/passwd - {type(e).__name__}")

# Test 2: Try to write to system directory
try:
    with open('/tmp/test.txt', 'w') as f:
        f.write("test")
    print("✅ OK: Can write to /tmp (expected)")
except Exception as e:
    print(f"❌ FAIL: Cannot write to /tmp - {type(e).__name__}")

# Test 3: List root directory
try:
    files = os.listdir('/')
    print(f"✅ OK: Can list / - {len(files)} entries")
    print(f"   Entries: {', '.join(files[:5])}...")
except Exception as e:
    print(f"❌ FAIL: Cannot list / - {type(e).__name__}")
"""

# Demo 7: Resource limits
DEMO_RESOURCE_LIMITS = """
import time

print("Testing resource limits...")

# Test 1: Memory allocation
print("\\n1. Memory test:")
try:
    # Try to allocate 1GB of memory
    big_list = [0] * (1024 * 1024 * 1024 // 8)
    print(f"❌ WARNING: Allocated 1GB of memory")
    del big_list
except MemoryError:
    print("✅ PASS: Memory limit enforced")

# Test 2: CPU intensive task
print("\\n2. CPU test (5 seconds):")
start = time.time()
count = 0
while time.time() - start < 5:
    count += 1
    # Busy loop
print(f"✅ Completed {count:,} iterations in 5 seconds")

print("\\nResource limit test complete!")
"""

# Demo 8: Output handling
DEMO_LARGE_OUTPUT = """
print("Testing large output handling...")

# Generate lots of output
for i in range(1000):
    print(f"Line {i}: " + "x" * 100)

print("\\nGenerated 1000 lines of output!")
"""

# Demo 9: Import capabilities
DEMO_IMPORTS = """
print("Testing available Python libraries...")

libraries = [
    'numpy', 'pandas', 'requests', 'matplotlib', 
    'scipy', 'sklearn', 'tensorflow', 'torch'
]

available = []
unavailable = []

for lib in libraries:
    try:
        __import__(lib)
        available.append(lib)
    except ImportError:
        unavailable.append(lib)

print(f"\\nAvailable libraries: {', '.join(available) or 'None'}")
print(f"Unavailable libraries: {', '.join(unavailable) or 'None'}")

# Test standard library
import json
import hashlib
import datetime

data = {"timestamp": datetime.datetime.now().isoformat()}
print(f"\\nJSON encoding works: {json.dumps(data)}")
print(f"SHA256 hash works: {hashlib.sha256(b'test').hexdigest()}")
"""

# Demo 10: Concurrent stress test
DEMO_STRESS_TEST = """
import random
import time

# Simulate variable workload
sleep_time = random.uniform(1, 3)
print(f"Evaluation {random.randint(1000, 9999)} starting...")
print(f"Will process for {sleep_time:.1f} seconds")

time.sleep(sleep_time)

# Generate some results
result = sum(range(random.randint(100, 1000)))
print(f"Completed! Result: {result}")
"""

# All demos for easy access
ALL_DEMOS = {
    "hello": ("Hello World", DEMO_HELLO_WORLD),
    "timeout": ("Timeout Test", DEMO_TIMEOUT),
    "syntax": ("Syntax Error", DEMO_SYNTAX_ERROR),
    "runtime": ("Runtime Error", DEMO_RUNTIME_ERROR),
    "network": ("Network Isolation", DEMO_NETWORK_ISOLATION),
    "filesystem": ("File System Isolation", DEMO_FILESYSTEM_ISOLATION),
    "resources": ("Resource Limits", DEMO_RESOURCE_LIMITS),
    "output": ("Large Output", DEMO_LARGE_OUTPUT),
    "imports": ("Import Test", DEMO_IMPORTS),
    "stress": ("Stress Test", DEMO_STRESS_TEST),
}

if __name__ == "__main__":
    print("Available demo scenarios:")
    for key, (name, _) in ALL_DEMOS.items():
        print(f"  {key}: {name}")
    
    print("\nTo use these in the UI, copy the code for any scenario.")
    print("For stress testing, submit the 'stress' scenario multiple times.")