# Container Isolation and Security

## Current Security Measures

Our execution engines implement defense-in-depth with multiple security layers:

### 1. Network Isolation (`--network none`)
- **What it does**: Completely disables network access
- **Prevents**: Data exfiltration, downloading malicious payloads, C&C communication
- **Test**: Code trying to access any network endpoint will fail

### 2. Filesystem Protection (`--read-only`)
- **What it does**: Makes entire container filesystem read-only
- **Prevents**: Writing malicious files, modifying system files, persistence
- **Exception**: Only `/tmp` might be writable (but we don't mount it)

### 3. Resource Limits
- **Memory**: `--memory 100m` - Max 100MB RAM
- **CPU**: `--cpus 0.5` - Max 50% of one CPU core
- **Prevents**: Resource exhaustion attacks, infinite loops consuming resources

### 4. Capability Dropping (`--cap-drop ALL`)
- **What it does**: Removes all Linux capabilities
- **Prevents**:
  - Creating raw sockets (no packet sniffing)
  - Changing file ownership/permissions
  - Mounting filesystems
  - Loading kernel modules
  - Changing user/group IDs

### 5. No Privilege Escalation (`--security-opt no-new-privileges`)
- **What it does**: Prevents gaining new privileges during execution
- **Prevents**:
  - Exploiting setuid/setgid binaries
  - Escalating through vulnerable system calls
  - Gaining capabilities not started with

### 6. User Namespace (in gVisor mode)
- **What it does**: Maps container root to unprivileged user
- **Prevents**: Container root from being actual root on host

## Docker Command Security Layers

```bash
docker run \
  --rm                          # Remove container after exit
  --network none                # No network access
  --memory 100m                 # Memory limit
  --memory-swap 100m           # No swap (prevents memory bypass)
  --cpus 0.5                   # CPU limit
  --read-only                  # Read-only root filesystem
  --cap-drop ALL               # Drop all capabilities
  --security-opt no-new-privileges  # No privilege escalation
  -v /code.py:/code.py:ro     # Mount code read-only
  python:3.11-slim \
  python /code.py
```

## gVisor Additional Security

When using gVisor runtime (`--runtime=runsc`):
- **User-space kernel**: Intercepts and filters system calls
- **Reduced attack surface**: Only ~200 of 400+ syscalls implemented
- **Additional isolation**: Runs in separate process with minimal privileges

## Testing Security

### Network Isolation Test
```python
import urllib.request
try:
    urllib.request.urlopen('http://google.com')
    print("❌ FAIL: Network accessible")
except:
    print("✅ PASS: Network blocked")
```

### Filesystem Test
```python
try:
    with open('/test.txt', 'w') as f:
        f.write('test')
    print("❌ FAIL: Filesystem writable")
except:
    print("✅ PASS: Filesystem read-only")
```

### Capability Test
```python
import os
try:
    os.setuid(0)  # Try to become root
    print("❌ FAIL: Could change UID")
except:
    print("✅ PASS: Cannot change UID")
```

## Future Enhancements

1. **Seccomp profiles**: Further restrict system calls
2. **AppArmor/SELinux**: Mandatory access control
3. **User namespaces**: Better UID/GID mapping
4. **Time limits**: Prevent long-running executions
5. **Disk I/O limits**: Prevent disk exhaustion

## Deployment Considerations

### Local Development
- Current setup is secure for local testing
- Network isolation prevents accidental data leaks

### Production Deployment
- Use Kubernetes SecurityContext for additional controls
- Consider Falco for runtime security monitoring
- Implement admission controllers for policy enforcement
- Use Pod Security Standards (restricted profile)