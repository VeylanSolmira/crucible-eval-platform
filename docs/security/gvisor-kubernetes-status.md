# gVisor Kubernetes Integration Status

## Current State (July 16, 2025)

### What's Implemented ✅
1. **RuntimeClass Definition**: Created `k8s/base/gvisor-runtimeclass.yaml`
2. **Dispatcher Updated**: Modified to use `runtime_class_name="gvisor"` for evaluation pods
3. **Kind Configuration**: Created `k8s/kind-with-gvisor.yaml` for gVisor-enabled clusters
4. **Kustomization Updated**: Added gvisor-runtimeclass.yaml to base resources

### What's Missing ❌
1. **gVisor Not Installed**: Current Kind cluster doesn't have gVisor runtime
2. **Tests Still Failing**: Filesystem isolation test expects stronger isolation than standard containers provide
3. **No Fallback Logic**: Dispatcher will fail if gVisor runtime isn't available

## Why gVisor is Critical

Without gVisor, evaluation pods can:
- ✅ Read system files like `/etc/passwd` (currently happening)
- ✅ See host kernel information via `/proc`
- ✅ Potentially exploit kernel vulnerabilities
- ❌ Only prevented from writing by read-only filesystem

With gVisor, evaluation pods:
- ❌ Cannot read host system files
- ❌ See only gVisor's emulated kernel
- ❌ Syscalls are intercepted and filtered
- ✅ Much stronger isolation for adversarial code

## Next Steps

### 1. Install gVisor in Development
For macOS development, options:
- Use Colima instead of Docker Desktop
- Set up Linux VM with gVisor
- Use remote Linux development server

### 2. Update Kind Cluster
```bash
# On a Linux host with gVisor installed:
kind create cluster --config k8s/kind-with-gvisor.yaml --name crucible-gvisor
```

### 3. Add Fallback Logic
Update dispatcher to check if gVisor is available:
```python
# Check if gvisor RuntimeClass exists
try:
    api_instance.read_runtime_class("gvisor")
    runtime_class_name = "gvisor"
except ApiException:
    logger.warning("gVisor RuntimeClass not found, using default runtime")
    runtime_class_name = None
```

### 4. Update Tests
Once gVisor is working, the filesystem isolation test should pass as-is, since gVisor will block access to `/etc/passwd`.

## Production Requirements

For production METR deployment:
1. **Mandatory**: gVisor must be installed on all nodes
2. **Validation**: Admission webhook to reject pods without gVisor
3. **Monitoring**: Alert if evaluation pods run without gVisor
4. **Documentation**: Clear setup instructions for operators

## Security Impact

Current security posture (without gVisor):
- Network: ✅ Fully isolated (NetworkPolicy working)
- Filesystem: ⚠️  Read-only but system files visible
- Kernel: ❌ Shared with host (major risk)

Target security posture (with gVisor):
- Network: ✅ Fully isolated
- Filesystem: ✅ Cannot read system files
- Kernel: ✅ Isolated via gVisor userspace kernel

## References
- [gVisor Setup Guide](./gvisor-setup-guide.md)
- [Kind gVisor Issue](https://github.com/kubernetes-sigs/kind/issues/1079)
- [gVisor Kubernetes Guide](https://gvisor.dev/docs/user_guide/quick_start/kubernetes/)