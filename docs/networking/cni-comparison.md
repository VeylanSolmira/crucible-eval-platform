# Container Network Interface (CNI) Comparison

## Overview
Different CNI plugins provide varying levels of NetworkPolicy support and features. This document compares CNI options for Kubernetes clusters, especially regarding network isolation capabilities.

## CNI Plugin Comparison

### AWS VPC CNI
- **NetworkPolicy Support**: Limited (requires additional configuration)
- **External Traffic Blocking**: ❌ No - only controls pod-to-pod traffic
- **Setup Complexity**: Medium (requires ENABLE_NETWORK_POLICY env var)
- **Performance**: High (native AWS networking)
- **Best For**: AWS EKS clusters that don't need internet blocking

**Key Limitation**: VPC CNI NetworkPolicy only controls cluster-internal traffic. External internet access is NOT blocked by NetworkPolicy.

### Calico
- **NetworkPolicy Support**: ✅ Full support
- **External Traffic Blocking**: ✅ Yes - can block all traffic including internet
- **Setup Complexity**: Medium
- **Performance**: Good
- **Best For**: Clusters requiring complete network isolation

**Installation on EKS**:
```bash
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml
```

### Cilium
- **NetworkPolicy Support**: ✅ Full support + L7 policies
- **External Traffic Blocking**: ✅ Yes
- **Setup Complexity**: High
- **Performance**: Excellent (eBPF-based)
- **Best For**: Advanced use cases, L7 filtering, observability

### Flannel
- **NetworkPolicy Support**: ❌ No
- **External Traffic Blocking**: ❌ No
- **Setup Complexity**: Low
- **Performance**: Good
- **Best For**: Simple clusters without security requirements

### Weave Net
- **NetworkPolicy Support**: ✅ Yes
- **External Traffic Blocking**: ✅ Yes
- **Setup Complexity**: Low
- **Performance**: Moderate
- **Best For**: Small to medium clusters

## Decision Matrix

| Requirement | AWS VPC CNI | Calico | Cilium | Flannel | Weave |
|-------------|-------------|---------|---------|----------|--------|
| Block pod-to-pod | ✅ | ✅ | ✅ | ❌ | ✅ |
| Block internet | ❌ | ✅ | ✅ | ❌ | ✅ |
| AWS EKS native | ✅ | ✅ | ✅ | ❌ | ✅ |
| Performance | High | Good | High | Good | Moderate |
| Complexity | Medium | Medium | High | Low | Low |

## Recommendations

1. **For AWS EKS with basic pod isolation**: Use AWS VPC CNI with NetworkPolicy enabled
2. **For complete network isolation (including internet)**: Add Calico alongside VPC CNI
3. **For advanced L7 policies and observability**: Consider Cilium
4. **For development/testing**: Flannel is simple but lacks security features