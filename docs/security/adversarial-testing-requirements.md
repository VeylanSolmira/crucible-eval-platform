# Adversarial AI Testing Requirements

## Key Principle: Never Run Adversarial AI Tests Without Production Security

When testing potentially adversarial AI models, **always use the full production security stack**. Development shortcuts that are acceptable for normal software are NOT acceptable for AI safety evaluation.

## Minimum Security Requirements for Adversarial Testing

1. **gVisor (runsc) runtime** - Userspace kernel isolation
2. **Non-root execution** - Run as nobody (65534:65534)
3. **Network isolation** - Complete network disconnection
4. **Read-only filesystem** - Prevent persistence
5. **Resource limits** - CPU/memory caps
6. **Monitoring** - Real-time behavior tracking
7. **No privilege escalation** - Security options enforced

## Platform Constraints

### Why Standard macOS Docker Desktop is Unsuitable

```
macOS with Docker Desktop:
Your macOS
    ↓
Docker Desktop Linux VM (limited access)
    ↓
Container (can only use runc)
    ❌ Cannot install gVisor in Docker Desktop VM
```

### macOS Workarounds for gVisor

While standard Docker Desktop doesn't support gVisor, there are workarounds:

1. **Colima** - Docker Desktop alternative with gVisor support
   ```bash
   colima start --runtime docker --gvisor
   ```
   ⚠️ **Still not recommended for adversarial testing** - Your valuable dev machine is at risk

2. **Linux VM** - Run Ubuntu/Debian in VirtualBox/VMware
   ✅ **Better isolation** but still on your machine

3. **Remote Docker** - Use a dedicated Linux server
   ✅ **Recommended** - Isolates risk from your development machine

**Security Note**: Even with these workarounds, running adversarial AI tests on your development machine is risky. A VM escape could compromise your entire system. Use dedicated, isolated infrastructure for adversarial testing.

### Suitable Environments

1. **Linux Servers** (Recommended)
   - Full control over kernel and runtime
   - Can install and configure gVisor
   - Direct hardware access
   - No virtualization overhead

2. **Cloud Instances**
   - Google Cloud Run (uses gVisor by default)
   - AWS EC2 with Ubuntu/Debian
   - Azure VMs with Linux

3. **Dedicated Linux Workstations**
   - For sensitive local testing
   - Full security stack available

## Model Size Considerations

Modern AI models present additional challenges:

- **LLMs**: Often 10-100GB+ in size
- **Memory Requirements**: May need 32GB+ RAM
- **GPU Requirements**: Many models need CUDA
- **Storage**: Model weights + evaluation artifacts

These requirements often make cloud deployment more practical anyway.

## Recommended Workflow

### Development (macOS/Windows OK)
```bash
# Use standard Docker for development
python extreme_mvp_gvisor.py --runtime=runc

# Test basic functionality
# Develop evaluation logic
# Create test suites
```

### Staging (Linux Required)
```bash
# Must have gVisor installed
python extreme_mvp_gvisor.py --runtime=runsc

# Test security features
# Verify isolation
# Performance testing
```

### Production (Linux + Full Stack Required)
```yaml
# Kubernetes deployment with:
- gVisor runtime class
- Network policies
- Pod security policies
- Resource quotas
- Audit logging
- Behavioral monitoring
```

## Security Philosophy

**"If you wouldn't run it in production, don't run it with adversarial AI"**

This means:
- No shortcuts on security
- No "just for testing" compromises
- No local execution of untrusted models
- Always assume the AI is trying to escape

## Practical Implications

1. **Separate Development from Adversarial Testing**
   - Develop evaluation logic with safe test cases
   - Only run adversarial tests in secured environments

2. **Use Cloud Services for Adversarial Work**
   - Let cloud providers handle infrastructure security
   - Leverage their gVisor deployments
   - Use their monitoring tools

3. **Never Trust Local Development Environments**
   - Your laptop is not a security boundary
   - VMs on laptops are not sufficient
   - Corporate networks are not isolated enough

## Example: Safe vs Unsafe Testing

### ✅ SAFE: Development Testing
```python
# On macOS with standard Docker
# Testing with known-safe evaluation code
def test_basic_math():
    result = evaluate("print(2 + 2)")
    assert result == "4"
```

### ❌ UNSAFE: Adversarial Testing on macOS
```python
# DO NOT DO THIS on macOS/development machines
def test_adversarial_model():
    untrusted_model = load_model("potential-escape-artist-v1")
    result = evaluate(untrusted_model.generate_code())
    # This model could be trying to escape!
```

### ✅ SAFE: Adversarial Testing in Production
```python
# On Linux with full security stack
# In isolated network segment
# With gVisor + monitoring + alerts
def test_adversarial_model():
    # Same code, but now in a proper security context
    untrusted_model = load_model("potential-escape-artist-v1")
    result = evaluate(untrusted_model.generate_code())
```

## Summary

- **Development**: Use any OS, focus on functionality
- **Adversarial Testing**: Linux + gVisor + full security stack ONLY
- **Model Size**: Often makes cloud deployment necessary anyway
- **Philosophy**: No security shortcuts with adversarial AI

The platform's fallback to standard Docker on macOS is for development convenience only. Never use it for actual adversarial AI evaluation.