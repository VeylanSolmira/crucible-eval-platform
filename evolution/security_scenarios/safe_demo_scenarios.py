"""
Safe Demo Scenarios - These won't harm your local system
These demonstrate security concepts without actually performing dangerous operations
"""

SAFE_DEMO_SCENARIOS = {
    "process_isolation_demo": {
        "name": "Process Isolation Demo",
        "description": "Shows process isolation without actual attacks",
        "code": """
import os
import sys

print("=== Process Isolation Demo ===")

# Safe: Just check our PID and environment
print(f"Running as PID: {os.getpid()}")
print(f"Python version: {sys.version}")

# Safe: Check if we're in a container (doesn't modify anything)
try:
    with open('/proc/self/cgroup', 'r') as f:
        cgroup_content = f.read()
        if 'docker' in cgroup_content or 'containerd' in cgroup_content:
            print("✅ Running inside a container")
        else:
            print("⚠️  Not in a container (or can't detect)")
except Exception as e:
    print(f"Cannot read cgroup: {e}")

# Safe: List environment variables (read-only)
env_count = len(os.environ)
print(f"Environment variables: {env_count}")

# Safe: Check filesystem (read-only)
if os.path.exists('/.dockerenv'):
    print("✅ Docker environment file found")
else:
    print("⚠️  No Docker environment file")
""",
        "expected_result": "informational",
        "threat_level": "none"
    },

    "network_check_demo": {
        "name": "Network Configuration Check",
        "description": "Checks network configuration without making connections",
        "code": """
import socket
import subprocess

print("=== Network Configuration Check ===")

# Safe: Get hostname
try:
    hostname = socket.gethostname()
    print(f"Hostname: {hostname}")
except Exception as e:
    print(f"Cannot get hostname: {e}")

# Safe: List network interfaces (read-only)
try:
    result = subprocess.run(['ip', 'addr', 'show'], 
                          capture_output=True, text=True, timeout=2)
    if result.returncode == 0:
        lines = result.stdout.strip().split('\\n')
        interfaces = [l for l in lines if ': ' in l and not l.startswith(' ')]
        print(f"Network interfaces: {len(interfaces)}")
        for iface in interfaces[:3]:  # Show first 3
            print(f"  - {iface.split(': ')[1].split('@')[0]}")
    else:
        print("Cannot list interfaces")
except Exception as e:
    print(f"ip command not available: {e}")

# Safe: Check if we can resolve DNS (doesn't connect)
try:
    # This only does DNS lookup, doesn't connect
    addr = socket.gethostbyname('localhost')
    print(f"localhost resolves to: {addr}")
except Exception as e:
    print(f"DNS resolution error: {e}")
""",
        "expected_result": "informational",
        "threat_level": "none"
    },

    "resource_limits_demo": {
        "name": "Resource Limits Check",
        "description": "Checks resource limits without exhausting them",
        "code": """
import resource
import os

print("=== Resource Limits Check ===")

# Safe: Just read current limits
try:
    # Memory limit
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    if hard == resource.RLIM_INFINITY:
        print("Memory limit: UNLIMITED")
    else:
        print(f"Memory limit: {hard / (1024*1024):.1f} MB")
    
    # Process limit
    soft, hard = resource.getrlimit(resource.RLIMIT_NPROC)
    if hard == resource.RLIM_INFINITY:
        print("Process limit: UNLIMITED")
    else:
        print(f"Process limit: {hard} processes")
    
    # File descriptor limit
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    print(f"File descriptor limit: {hard}")
    
except Exception as e:
    print(f"Cannot read resource limits: {e}")

# Safe: Check CPU count
try:
    cpu_count = os.cpu_count()
    print(f"CPU cores visible: {cpu_count}")
except Exception as e:
    print(f"Cannot get CPU count: {e}")

# Safe: Check available memory (doesn't allocate)
try:
    with open('/proc/meminfo', 'r') as f:
        for line in f:
            if line.startswith('MemAvailable'):
                mem_kb = int(line.split()[1])
                print(f"Memory available: {mem_kb / 1024:.1f} MB")
                break
except Exception as e:
    print(f"Cannot read memory info: {e}")
""",
        "expected_result": "informational",
        "threat_level": "none"
    },

    "filesystem_readonly_demo": {
        "name": "Filesystem Permissions Check",
        "description": "Checks filesystem permissions without writing",
        "code": """
import os
import tempfile

print("=== Filesystem Permissions Check ===")

# Safe: Check if root filesystem is read-only
paths_to_check = [
    ('/', 'Root filesystem'),
    ('/etc', 'System config'),
    ('/tmp', 'Temp directory'),
    ('/home', 'Home directory')
]

for path, description in paths_to_check:
    if os.path.exists(path):
        # Check if writable (doesn't actually write)
        if os.access(path, os.W_OK):
            print(f"⚠️  {description} ({path}): Writable")
        else:
            print(f"✅ {description} ({path}): Read-only")
    else:
        print(f"   {description} ({path}): Not found")

# Safe: Check temp directory
try:
    temp_dir = tempfile.gettempdir()
    print(f"\\nTemp directory: {temp_dir}")
    
    # List temp files (read-only)
    temp_files = os.listdir(temp_dir)
    print(f"Files in temp: {len(temp_files)}")
except Exception as e:
    print(f"Cannot check temp directory: {e}")
""",
        "expected_result": "informational",
        "threat_level": "none"
    },

    "capability_info_demo": {
        "name": "Process Capabilities Information",
        "description": "Shows process capabilities without trying to escalate",
        "code": """
import os
import subprocess

print("=== Process Capabilities Information ===")

# Safe: Read our own capabilities
try:
    with open('/proc/self/status', 'r') as f:
        for line in f:
            if line.startswith('Cap'):
                print(line.strip())
except Exception as e:
    print(f"Cannot read process status: {e}")

# Safe: Check our user/group
print(f"\\nRunning as UID: {os.getuid()}, GID: {os.getgid()}")

# Safe: Check if we're root (doesn't change anything)
if os.getuid() == 0:
    print("⚠️  Running as root!")
else:
    print("✅ Not running as root")

# Safe: List available commands (doesn't run them)
dangerous_commands = ['sudo', 'su', 'mount', 'modprobe', 'insmod']
for cmd in dangerous_commands:
    try:
        result = subprocess.run(['which', cmd], 
                              capture_output=True, text=True, timeout=1)
        if result.returncode == 0:
            print(f"⚠️  Found: {cmd}")
        else:
            print(f"✅ Not found: {cmd}")
    except:
        print(f"✅ Not found: {cmd}")
""",
        "expected_result": "informational",
        "threat_level": "none"
    }
}