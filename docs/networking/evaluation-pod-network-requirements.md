# Evaluation Pod Network Requirements

## Overview
This document outlines the network requirements for evaluation pods and how to properly implement NetworkPolicy without breaking functionality.

## Current Issues with Evaluation NetworkPolicies

### 1. Complete Egress Block
```yaml
# CURRENT (BROKEN)
egress: []  # Blocks ALL traffic including DNS, logs, results
```

This configuration prevents evaluation pods from:
- ❌ Resolving DNS names
- ❌ Sending logs to Fluent Bit
- ❌ Returning results to storage service
- ❌ Reporting status to dispatcher

### 2. Missing Essential Services
The crucible-platform pods also can't access:
- Redis (for task queuing)
- Postgres (for state storage)
- Storage service (for results)
- Other microservices

## Required Network Access

### For Evaluation Pods

#### 1. DNS (Essential)
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

#### 2. Logging Infrastructure
```yaml
- to:
  - namespaceSelector:
      matchLabels:
        name: dev  # or your namespace
  - podSelector:
      matchLabels:
        app: fluent-bit
  ports:
  - protocol: TCP
    port: 24224  # Fluent Bit forward port
```

#### 3. Storage Service (for results)
```yaml
- to:
  - podSelector:
      matchLabels:
        app: storage-service
  ports:
  - protocol: TCP
    port: 8082
```

#### 4. Status Reporting (if applicable)
```yaml
- to:
  - podSelector:
      matchLabels:
        app: dispatcher
  ports:
  - protocol: TCP
    port: 8090
```

### For Platform Pods

#### 1. Redis Access
```yaml
- to:
  - podSelector:
      matchLabels:
        app: redis
  ports:
  - protocol: TCP
    port: 6379
- to:
  - podSelector:
      matchLabels:
        app: celery-redis
  ports:
  - protocol: TCP
    port: 6379
```

#### 2. Postgres Access
```yaml
- to:
  - podSelector:
      matchLabels:
        app: postgres
  ports:
  - protocol: TCP
    port: 5432
```

#### 3. Inter-Service Communication
```yaml
- to:
  - podSelector:
      matchLabels:
        app: storage-service
  ports:
  - protocol: TCP
    port: 8082
- to:
  - podSelector:
      matchLabels:
        app: api-service
  ports:
  - protocol: TCP
    port: 8080
```

## Corrected NetworkPolicy Examples

### Evaluation Pod Policy
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: evaluation-pod-isolation
  namespace: dev
spec:
  podSelector:
    matchLabels:
      app: evaluation
  policyTypes:
  - Ingress
  - Egress
  
  ingress:
  # Allow from dispatcher/platform
  - from:
    - podSelector:
        matchLabels:
          app: crucible-platform
    ports:
    - protocol: TCP
      port: 9000
  
  egress:
  # DNS
  - to:
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
  
  # Logging
  - to:
    - namespaceSelector:
        matchLabels:
          name: dev
    - podSelector:
        matchLabels:
          app: fluent-bit
    ports:
    - protocol: TCP
      port: 24224
  
  # Storage service for results
  - to:
    - podSelector:
        matchLabels:
          app: storage-service
    ports:
    - protocol: TCP
      port: 8082
  
  # Note: External internet access will still work on AWS VPC CNI
  # Add Calico if you need to block internet access
```

### Platform Services Policy
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: platform-services-policy
  namespace: dev
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/part-of: crucible-platform
  policyTypes:
  - Ingress
  - Egress
  
  ingress:
  # From ingress controller
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8080
  
  # From other platform services
  - from:
    - podSelector:
        matchLabels:
          app.kubernetes.io/part-of: crucible-platform
  
  egress:
  # DNS
  - to:
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
  
  # All platform services can talk to each other
  - to:
    - podSelector:
        matchLabels:
          app.kubernetes.io/part-of: crucible-platform
  
  # Databases
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - podSelector:
        matchLabels:
          app: celery-redis
    ports:
    - protocol: TCP
      port: 6379
  
  # Evaluation pods
  - to:
    - podSelector:
        matchLabels:
          app: evaluation
    ports:
    - protocol: TCP
      port: 9000
  
  # Logging
  - to:
    - namespaceSelector:
        matchLabels:
          name: dev
    - podSelector:
        matchLabels:
          app: fluent-bit
```

## Testing Strategy

### 1. Deploy Without Enforcement First
```bash
# Apply policies but check if they would work
kubectl apply -f network-policies.yaml --dry-run=server
```

### 2. Test Individual Services
```bash
# Test DNS
kubectl exec -it test-pod -- nslookup kubernetes.default

# Test service connectivity
kubectl exec -it test-pod -- curl storage-service:8082/health

# Test logging
kubectl exec -it test-pod -- echo "test log" | nc fluent-bit 24224
```

### 3. Monitor for Failures
```bash
# Watch for connection timeouts
kubectl logs -f deployment/dispatcher | grep -i "timeout\|refused\|failed"

# Check if results are being stored
kubectl logs -f deployment/storage-worker
```

## Migration Plan

1. **Phase 1**: Update NetworkPolicies to include required access
2. **Phase 2**: Test in development environment thoroughly
3. **Phase 3**: Apply with monitoring and quick rollback plan
4. **Phase 4**: Consider Calico for internet blocking if needed

## Important Notes

1. **AWS VPC CNI Limitation**: Internet access will NOT be blocked even with `egress: []`
2. **Race Conditions**: NetworkPolicy enforcement may have delays with Job pods
3. **Logging is Critical**: Always allow access to logging infrastructure
4. **DNS is Essential**: Never block DNS unless you use IP addresses everywhere