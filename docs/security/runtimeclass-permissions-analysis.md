# Security Analysis: RuntimeClass Read Permissions for Dispatcher

## Overview
The dispatcher service requires read access to RuntimeClass resources to check for gVisor availability. This document analyzes the security implications of granting these permissions.

## Permission Details
```yaml
- apiGroups: ["node.k8s.io"]
  resources: ["runtimeclasses"]
  verbs: ["get", "list"]
```

## What are RuntimeClasses?
RuntimeClasses are Kubernetes resources that allow selection of different container runtime configurations. Common examples include:
- **gVisor**: User-space kernel providing strong isolation
- **Kata Containers**: Lightweight VMs for container isolation
- **Default**: Standard container runtime (containerd/CRI-O)

## Security Analysis

### 1. Access Level: Read-Only (Low Risk)
- **Granted**: `get`, `list` operations only
- **Not Granted**: `create`, `update`, `delete`, `patch`
- **Impact**: Service can discover available runtimes but cannot modify them
- **Risk Level**: **Low** - No ability to weaken security configurations

### 2. Scope: Cluster-Wide Resource
- RuntimeClasses are cluster-scoped (not namespaced)
- Requires ClusterRole instead of Role
- Dispatcher can enumerate all runtime configurations
- **Risk Level**: **Low** - Typically only 2-5 RuntimeClasses exist

### 3. Information Disclosure Risks
An attacker compromising the dispatcher could discover:
- Available security runtimes (gVisor, Kata, etc.)
- Runtime handler names and configurations
- Node selector requirements for specific runtimes

**Mitigations**:
- This information is not sensitive
- Knowing available runtimes doesn't help bypass them
- Runtime configurations are typically documented anyway

### 4. Principle of Least Privilege Compliance
The dispatcher needs this permission to:
- Check if gVisor is available before creating jobs
- Fall back gracefully in development environments
- Provide appropriate error messages

Without this permission, we would need to:
- **Hardcode assumptions**: Brittle and environment-specific
- **Skip security features**: Might not use gVisor when available
- **Generate noisy logs**: Constant permission denied errors

### 5. Alternative Approaches Considered

#### Option A: ConfigMap-Based Discovery
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: runtime-config
data:
  gvisor_available: "true"
```
- **Pros**: No cluster-wide permissions needed
- **Cons**: Manual updates required, can drift from reality

#### Option B: Environment Variable
```yaml
env:
- name: GVISOR_AVAILABLE
  value: "true"
```
- **Pros**: Simple, no permissions needed
- **Cons**: Static configuration, different per environment

#### Option C: Try and Fail
```python
# Always try gVisor, handle failures
job.spec.runtimeClassName = "gvisor"  # Might fail
```
- **Pros**: No read permissions needed
- **Cons**: Noisy logs, poor error messages, harder debugging

## Threat Modeling

### Attack Scenario 1: Dispatcher Compromise
If an attacker gains control of the dispatcher pod:
- **Can**: List available RuntimeClasses
- **Cannot**: Create malicious RuntimeClasses
- **Cannot**: Modify existing RuntimeClasses
- **Cannot**: Force jobs to use weaker isolation

### Attack Scenario 2: Supply Chain Attack
If the dispatcher image is compromised:
- RuntimeClass read access doesn't increase attack surface
- Attacker already has job creation permissions (more dangerous)
- Runtime enumeration provides minimal additional value

### Attack Scenario 3: Privilege Escalation
- Reading RuntimeClasses cannot lead to privilege escalation
- No sensitive data exposed (no secrets, tokens, or credentials)
- Cannot be used to pivot to other resources

## Recommendations

### 1. Grant the Permission ✅
The read-only RuntimeClass permission is justified because:
- Enables adaptive security based on environment
- Follows principle of least privilege
- Risk is minimal and well-understood
- Alternatives are worse from operational perspective

### 2. Additional Security Measures
- **Audit Logging**: Log all RuntimeClass access attempts
- **Network Policies**: Restrict dispatcher's network access
- **Pod Security Standards**: Enforce restrictions on dispatcher pod
- **Regular Reviews**: Audit RBAC permissions quarterly

### 3. Monitoring
Watch for:
- Excessive RuntimeClass list operations (potential reconnaissance)
- Failed gVisor job creation after successful detection
- Dispatcher pods running without expected service account

## Conclusion
Granting read access to RuntimeClasses is a reasonable security trade-off that enables the dispatcher to make intelligent decisions about job isolation without significantly increasing the attack surface. The permission aligns with the principle of least privilege while supporting the platform's security goals.

## Implementation
```bash
# Apply the permission
kubectl apply -f k8s/overlays/local/dispatcher-clusterrole.yaml

# Verify the permission
kubectl auth can-i get runtimeclasses --as=system:serviceaccount:crucible:job-dispatcher

# Test functionality
kubectl logs -n crucible deployment/dispatcher | grep -i gvisor
```