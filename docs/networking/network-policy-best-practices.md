# NetworkPolicy Best Practices

## Overview
NetworkPolicies in Kubernetes are whitelists, not blacklists. They define what traffic IS allowed, not what's blocked. This document covers best practices for implementing NetworkPolicies.

## Key Concepts

### NetworkPolicies are Additive
- Multiple policies can apply to the same pod
- Traffic is allowed if ANY policy allows it
- You cannot "subtract" permissions with additional policies

### Default Behavior
- Without NetworkPolicy: All traffic is allowed
- With NetworkPolicy: Only explicitly allowed traffic is permitted

## Essential Traffic to Allow

### 1. DNS Access (Required for Almost Everything)
```yaml
egress:
- to:
  - namespaceSelector: {}
    podSelector:
      matchLabels:
        k8s-app: kube-dns
  ports:
  - protocol: UDP
    port: 53
  - protocol: TCP
    port: 53
```

### 2. Logging Infrastructure
```yaml
egress:
- to:
  - namespaceSelector:
      matchLabels:
        name: logging
  - podSelector:
      matchLabels:
        app: fluent-bit
```

### 3. Service-to-Service Communication
```yaml
# API to Database
egress:
- to:
  - podSelector:
      matchLabels:
        app: postgres
  ports:
  - protocol: TCP
    port: 5432
```

## Common Patterns

### Default Deny All
Start with denying everything, then add specific allows:

```yaml
# 1. Default deny for namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}  # Applies to all pods
  policyTypes:
  - Ingress
  - Egress
---
# 2. Then add specific allows
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    - podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
```

### Frontend-Backend-Database Pattern
```yaml
# Frontend can only talk to API
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-policy
spec:
  podSelector:
    matchLabels:
      tier: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          tier: api
    ports:
    - protocol: TCP
      port: 8080
  # Always allow DNS
  - to:
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
---
# API can talk to database
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-policy
spec:
  podSelector:
    matchLabels:
      tier: api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          tier: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          tier: database
    ports:
    - protocol: TCP
      port: 5432
  # DNS
  - to:
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
```

## Common Mistakes

### 1. Blocking DNS
```yaml
# BAD: No DNS access
egress: []  # Blocks EVERYTHING including DNS

# GOOD: Allow DNS
egress:
- to:
  - namespaceSelector: {}
    podSelector:
      matchLabels:
        k8s-app: kube-dns
  ports:
  - protocol: UDP
    port: 53
```

### 2. Forgetting Monitoring/Logging
Pods need to send logs and metrics:
```yaml
egress:
# ... other rules ...
- to:
  - namespaceSelector:
      matchLabels:
        name: monitoring
- to:
  - namespaceSelector:
      matchLabels:
        name: logging
```

### 3. Not Testing Incrementally
- Start with logging what would be blocked
- Apply policies to test namespaces first
- Roll out gradually with monitoring

### 4. Assuming External Traffic is Blocked
- Many CNIs (like AWS VPC CNI) only control internal traffic
- External internet access may still work despite egress: []
- Use additional controls for internet blocking

## Testing NetworkPolicies

### 1. Test Pod Creation
```bash
# Create a test pod with specific labels
kubectl run test-netpol \
  --image=nicolaka/netshoot \
  -l app=myapp \
  --rm -it \
  -- /bin/bash

# Inside the pod, test connections
curl http://some-service:8080
nslookup some-service
```

### 2. Verify Policy is Applied
```bash
# Check if NetworkPolicy exists
kubectl get networkpolicy -n namespace

# Describe to see which pods it affects
kubectl describe networkpolicy policy-name -n namespace
```

### 3. Check CNI Support
```bash
# AWS VPC CNI specific
kubectl get policyendpoints -n namespace

# General - check for policy controllers
kubectl get pods -n kube-system | grep -E "calico|cilium|weave|policy"
```

## Migration Strategy

1. **Audit Current Traffic**
   - Use tools like Cilium Hubble or Calico flow logs
   - Understand actual communication patterns

2. **Create Policies in Report Mode**
   - Some CNIs support audit/report mode
   - Log what would be blocked without enforcing

3. **Apply to Test Environment**
   - Test all user journeys
   - Monitor for broken functionality

4. **Gradual Rollout**
   - Start with non-critical namespaces
   - Add policies incrementally
   - Have rollback plan ready

## Debugging

### When Things Don't Work

1. **Check DNS First**
   ```bash
   kubectl exec pod-name -- nslookup kubernetes.default
   ```

2. **Verify Labels Match**
   ```bash
   kubectl get pods --show-labels
   kubectl describe networkpolicy
   ```

3. **Test Without Policy**
   ```bash
   kubectl delete networkpolicy --all -n namespace
   # Test again
   ```

4. **Check CNI Logs**
   ```bash
   # AWS VPC CNI
   kubectl logs -n kube-system -l k8s-app=aws-node
   
   # Calico
   kubectl logs -n calico-system -l k8s-app=calico-node
   ```

Remember: NetworkPolicies are about defining allowed communication paths, not blocking specific traffic. Think in terms of "what should be allowed" rather than "what should be blocked".