# gVisor Setup Guide

## What is gVisor?

gVisor is Google's application kernel that provides an additional layer of isolation between running applications and the host operating system. It's used by Google Cloud Run and other Google services to safely run untrusted code.

## Why gVisor for AI Evaluation?

When evaluating potentially dangerous AI models, we need defense-in-depth:

### Standard Docker (runc)
```
AI Model Code
    ↓ (syscalls)
Linux Kernel  ← Shared attack surface!
    ↓
Hardware
```

### With gVisor (runsc)
```
AI Model Code
    ↓ (syscalls)
gVisor Kernel (userspace)  ← Intercepts everything
    ↓ (limited syscalls)
Linux Kernel
    ↓
Hardware
```

gVisor provides:
- **Syscall interception**: All system calls go through gVisor first
- **Reduced attack surface**: Only ~50 host syscalls vs ~350 in Linux
- **Userspace implementation**: Kernel exploits hit gVisor, not host
- **Production-tested**: Used by Google for untrusted workloads

## Installation

### Check if Already Installed

```bash
# Check if runsc runtime is available
docker run --rm --runtime=runsc alpine echo "gVisor is installed!"

# Or check Docker info
docker info | grep -A 5 "Runtimes:"
```

### macOS Installation

**Note**: gVisor requires Linux. Here are several approaches to use it on macOS:

#### Option 1: Colima (Recommended)
[Colima](https://github.com/abiosoft/colima) is a Docker Desktop alternative that supports gVisor:

```bash
# Install Colima
brew install colima

# Start Colima with gVisor support
colima start --runtime docker --arch x86_64 --cpu 4 --memory 8 --vm-type vz --vz-rosetta --network-address

# Set Docker context to use Colima
export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"

# Verify gVisor is available
docker run --rm --runtime=runsc alpine echo "gVisor works!"
```

**Note**: You may need to use `--arch x86_64` on Apple Silicon as gVisor primarily supports x86_64.

#### Option 2: Dedicated Linux VM
Use VirtualBox, VMware, or UTM to run a full Linux VM:

```bash
# Example with multipass
multipass launch --name gvisor-vm --cpus 4 --memory 8G --disk 40G ubuntu

# Connect to VM
multipass shell gvisor-vm

# Install Docker and gVisor (follow Linux instructions below)
# Then use the VM for testing
```

#### Option 3: Remote Docker Context
Point your local Docker to a remote Linux machine:

```bash
# Set up SSH access to Linux server
ssh-copy-id user@remote-linux-server

# Create Docker context
docker context create remote --docker "host=ssh://user@remote-linux-server"

# Use remote context
docker context use remote

# Now docker commands run on the remote machine
docker run --runtime=runsc alpine echo "Running on remote!"
```

#### Option 4: Cloud Development
Use a cloud instance for gVisor testing:

```bash
# Example: Google Cloud Shell (has gVisor pre-configured)
# Or spin up an EC2/GCP/Azure instance
```

#### For Quick Development
If you just need to test basic functionality:
```bash
# The platform falls back gracefully
python extreme_mvp_gvisor.py --runtime=runc
```

### Linux Installation

#### Ubuntu/Debian
```bash
# Add gVisor repository
curl -fsSL https://gvisor.dev/archive.key | sudo apt-key add -
sudo add-apt-repository "deb https://storage.googleapis.com/gvisor/releases release main"
sudo apt-get update

# Install
sudo apt-get install -y runsc

# Configure Docker
sudo runsc install
sudo systemctl restart docker
```

#### Other Linux Distributions
```bash
# Download binary
wget https://storage.googleapis.com/gvisor/releases/release/latest/$(uname -m)/runsc
chmod +x runsc
sudo mv runsc /usr/local/bin/

# Configure Docker
sudo runsc install
sudo systemctl restart docker
```

### Verify Installation

```bash
# Test gVisor runtime
docker run --rm --runtime=runsc alpine uname -a

# Should output something like:
# Linux <container-id> 4.4.0 #1 SMP <date> x86_64 Linux
# (Note the 4.4.0 kernel version - that's gVisor's emulated kernel)
```

## Using gVisor in the Platform

### Default Behavior

Our platform automatically detects and uses gVisor if available:

```bash
# Will use gVisor if installed, otherwise falls back to runc
python extreme_mvp_gvisor.py

# Force specific runtime
python extreme_mvp_gvisor.py --runtime=runsc  # Force gVisor
python extreme_mvp_gvisor.py --runtime=runc   # Force standard Docker
```

### Security Comparison

| Feature | Standard Docker (runc) | gVisor (runsc) |
|---------|----------------------|----------------|
| Kernel Sharing | Shares host kernel | Userspace kernel |
| Syscall Access | All ~350 syscalls | Only ~50 syscalls |
| Performance | Native | 10-20% overhead |
| Security | Good | Excellent |
| Use Case | Trusted code | Untrusted code |

### What gVisor Protects Against

1. **Kernel Exploits**: Container breakouts via kernel vulnerabilities
2. **Syscall Fuzzing**: AI models probing for kernel weaknesses
3. **Resource Exhaustion**: Better resource isolation
4. **Side Channels**: Reduced attack surface for timing attacks

## Production Configuration

For production AI evaluation, always use gVisor with additional hardening:

```python
docker_cmd = [
    'docker', 'run',
    '--runtime', 'runsc',           # gVisor runtime
    '--user', '65534:65534',        # Non-root user
    '--network', 'none',            # No network
    '--memory', '100m',             # Memory limit
    '--cpus', '0.5',               # CPU limit
    '--read-only',                 # Read-only filesystem
    '--security-opt', 'no-new-privileges',
    'python:3.11-slim',
    'python', '/code.py'
]
```

## Troubleshooting

### "unknown runtime: runsc"
- gVisor not installed or Docker not configured
- Follow installation steps above

### Performance Issues
- gVisor adds 10-20% overhead
- Normal for CPU-intensive workloads
- Still worth it for security

### Compatibility Issues
- Some syscalls not implemented
- Most Python code works fine
- Check [gVisor compatibility](https://gvisor.dev/docs/user_guide/compatibility/)

## Learn More

- [gVisor Documentation](https://gvisor.dev/docs/)
- [gVisor Architecture](https://gvisor.dev/docs/architecture_guide/)
- [Google Cloud Run Security](https://cloud.google.com/run/docs/container-contract)
- [OCI Runtime Spec](https://github.com/opencontainers/runtime-spec)

## Summary

For AI safety evaluation, gVisor provides essential additional isolation. While you can develop and test without it, production deployments should always use gVisor to protect against potentially adversarial AI models attempting to escape their sandbox.