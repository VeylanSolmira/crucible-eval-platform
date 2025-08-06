# Network Isolation Alternatives

## Overview
When NetworkPolicy isn't sufficient or available, there are alternative approaches to achieve network isolation for containers. This document covers various methods beyond traditional NetworkPolicy.

## Runtime-Level Isolation

### 1. gVisor
Provides network isolation at the syscall level:
```yaml
apiVersion: v1
kind: Pod
spec:
  runtimeClassName: gvisor
  containers:
  - name: isolated-container
    image: myapp
```

**Pros**:
- Blocks network at kernel level
- Works regardless of CNI
- Additional security benefits

**Cons**:
- Performance overhead
- Compatibility issues with some applications

### 2. Kata Containers
VM-level isolation:
```yaml
apiVersion: v1
kind: Pod
spec:
  runtimeClassName: kata
  containers:
  - name: isolated-container
    image: myapp
```

**Pros**:
- Strong isolation (VM boundaries)
- Network isolation included

**Cons**:
- Higher resource usage
- Slower startup

## Security Context Controls

### 1. Drop Network Capabilities
```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: app
    securityContext:
      capabilities:
        drop:
        - NET_RAW      # Prevents raw socket creation
        - NET_ADMIN    # Prevents network configuration
        - NET_BIND_SERVICE # Prevents binding to privileged ports
      runAsNonRoot: true
      allowPrivilegeEscalation: false
```

**Limitations**: Only prevents certain network operations, doesn't block all traffic

### 2. seccomp Profiles
```yaml
apiVersion: v1
kind: Pod
spec:
  securityContext:
    seccompProfile:
      type: Localhost
      localhostProfile: "profiles/no-network.json"
  containers:
  - name: app
    image: myapp
```

Example no-network.json profile:
```json
{
  "defaultAction": "SCMP_ACT_ALLOW",
  "syscalls": [
    {
      "names": ["socket", "connect", "bind", "listen"],
      "action": "SCMP_ACT_ERRNO",
      "errno": "EPERM"
    }
  ]
}
```

## iptables-Based Isolation

### Init Container Approach
```yaml
apiVersion: v1
kind: Pod
spec:
  initContainers:
  - name: network-blocker
    image: alpine
    securityContext:
      capabilities:
        add: ["NET_ADMIN"]
    command:
    - sh
    - -c
    - |
      apk add iptables
      # Block all outbound traffic
      iptables -P OUTPUT DROP
      iptables -P FORWARD DROP
      # Allow only loopback
      iptables -A OUTPUT -o lo -j ACCEPT
      # Save rules
      iptables-save > /etc/iptables/rules.v4
    volumeMounts:
    - name: iptables
      mountPath: /etc/iptables
  containers:
  - name: app
    image: myapp
    securityContext:
      capabilities:
        add: ["NET_ADMIN"]
    volumeMounts:
    - name: iptables
      mountPath: /etc/iptables
  volumes:
  - name: iptables
    emptyDir: {}
```

## Network Namespace Isolation

### Custom Network Namespace
```yaml
apiVersion: v1
kind: Pod
spec:
  hostNetwork: false  # Use pod network namespace
  dnsPolicy: None     # No DNS
  dnsConfig:
    nameservers: []   # Empty DNS servers
  containers:
  - name: app
    image: myapp
```

## Service Mesh Policies

### Istio Authorization Policies
```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: default
spec:
  # Deny all traffic by default
  rules: []
---
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: allow-specific
spec:
  selector:
    matchLabels:
      app: myapp
  action: ALLOW
  rules:
  - to:
    - operation:
        hosts: ["internal-service.default.svc.cluster.local"]
```

### Linkerd Traffic Policies
```yaml
apiVersion: policy.linkerd.io/v1beta1
kind: ServerAuthorization
metadata:
  name: only-allow-frontend
  namespace: backend
spec:
  server:
    name: backend-server
  client:
    meshTLS:
      identities:
      - "frontend.frontend.serviceaccount.identity.linkerd.cluster.local"
```

## AWS-Specific Solutions

### Security Groups for Pods
```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    vpc.amazonaws.com/pod-sg: "sg-xxxxx"
spec:
  containers:
  - name: app
    image: myapp
```

Security Group rules:
```bash
# Create security group with no egress rules
aws ec2 create-security-group \
  --group-name isolated-pods \
  --description "No egress allowed"

# Remove default egress rule
aws ec2 revoke-security-group-egress \
  --group-id sg-xxxxx \
  --ip-permissions '[{"IpProtocol":"-1","IpRanges":[{"CidrIp":"0.0.0.0/0"}]}]'
```

## Comparison Matrix

| Method | Blocks Internal | Blocks External | Performance Impact | Complexity |
|--------|-----------------|-----------------|-------------------|------------|
| NetworkPolicy | ✅ | Depends on CNI | Low | Medium |
| gVisor | ✅ | ✅ | Medium | Low |
| Kata Containers | ✅ | ✅ | High | Medium |
| Drop Capabilities | Partial | Partial | None | Low |
| iptables | ✅ | ✅ | Low | High |
| Service Mesh | ✅ | ✅ | Medium | High |
| AWS Security Groups | ✅ | ✅ | Low | Medium |

## Recommendations

1. **For complete isolation**: Use gVisor or Kata Containers
2. **For AWS EKS**: Combine VPC CNI NetworkPolicy with Security Groups for Pods
3. **For granular control**: Use a service mesh like Istio
4. **For simple cases**: Drop network capabilities and use restricted security contexts
5. **For emergency isolation**: Use iptables in init containers

## Testing Isolation

```bash
# Test script to verify isolation
cat <<'EOF' > test-isolation.sh
#!/bin/bash
echo "Testing network isolation..."

# Test internal DNS
echo -n "DNS resolution: "
nslookup kubernetes.default > /dev/null 2>&1 && echo "FAIL" || echo "PASS"

# Test internal service
echo -n "Internal service: "
curl -s --max-time 2 http://kubernetes.default:443 > /dev/null 2>&1 && echo "FAIL" || echo "PASS"

# Test external
echo -n "External access: "
curl -s --max-time 2 http://google.com > /dev/null 2>&1 && echo "FAIL" || echo "PASS"

# Test raw sockets
echo -n "Raw sockets: "
python3 -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_RAW, 1)" 2>/dev/null && echo "FAIL" || echo "PASS"
EOF

kubectl exec test-pod -- bash /test-isolation.sh
```

Remember: Defense in depth is key. Combine multiple approaches for maximum security.