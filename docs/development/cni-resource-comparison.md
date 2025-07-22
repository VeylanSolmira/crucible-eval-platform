# CNI Resource Usage Comparison

## Actual Resource Usage

### kindnet (Kind's default)
- **Per node**: ~30-50MB RAM
- **CPU**: Negligible (< 0.01 cores)
- **Functionality**: Basic pod networking only
- **Pods**: 1 pod per node

### Calico
- **Per node**: ~150-250MB RAM
- **CPU**: 0.05-0.1 cores idle, up to 0.5 cores under load
- **Functionality**: Full NetworkPolicy, BGP routing, IPIP/VXLAN encapsulation
- **Pods**: 
  - calico-node (DaemonSet): ~150MB per node
  - calico-kube-controllers: ~50MB (1 replica)
  - calico-typha (optional): ~100MB per replica

### Cilium
- **Per node**: ~250-400MB RAM
- **CPU**: 0.1-0.2 cores idle, up to 1 core under load
- **Functionality**: NetworkPolicy, L7 policies, eBPF-based dataplane, observability
- **Pods**:
  - cilium-agent (DaemonSet): ~250MB per node
  - cilium-operator: ~100MB (2 replicas by default)
  - hubble-relay (optional): ~50MB
  - hubble-ui (optional): ~100MB

## Real-World Example (3-node Kind cluster)

### kindnet
```
NAME              CPU    MEMORY
kindnet-node1     1m     35Mi
kindnet-node2     1m     32Mi
kindnet-node3     1m     33Mi
--------------------------
TOTAL:            3m     100Mi
```

### Calico
```
NAME                          CPU    MEMORY
calico-node-node1             25m    156Mi
calico-node-node2             23m    148Mi
calico-node-node3             24m    152Mi
calico-kube-controllers       15m    52Mi
calico-typha-1                10m    98Mi
calico-typha-2                10m    96Mi
---------------------------------------
TOTAL:                        107m   702Mi  (7x kindnet)
```

### Cilium
```
NAME                      CPU    MEMORY
cilium-agent-node1        45m    287Mi
cilium-agent-node2        42m    276Mi
cilium-agent-node3        44m    281Mi
cilium-operator-1         20m    112Mi
cilium-operator-2         18m    108Mi
hubble-relay             15m     56Mi
---------------------------------------
TOTAL:                   184m   1120Mi  (11x kindnet)
```

## Why the Difference?

### kindnet
- Simple bridge networking
- No packet filtering
- No policy enforcement
- Minimal features = minimal resources

### Calico
- Maintains routing tables
- Enforces NetworkPolicies via iptables
- BGP daemon for route distribution
- IPIP/VXLAN encapsulation overhead
- Connection tracking state

### Cilium
- eBPF programs loaded in kernel
- Connection state tracking
- L7 protocol parsing (HTTP, gRPC, etc.)
- Hubble observability data collection
- More advanced features = more memory

## Impact on Development Machine

On a typical development machine with 16GB RAM:

### With kindnet (default)
- Kubernetes control plane: ~800MB
- 3 worker nodes: ~1.5GB
- kindnet: ~100MB
- **Total cluster**: ~2.4GB

### With Calico
- Same base cluster: ~2.3GB
- Calico: ~700MB
- **Total cluster**: ~3.0GB (+600MB)

### With Cilium
- Same base cluster: ~2.3GB
- Cilium: ~1.1GB
- **Total cluster**: ~3.4GB (+1GB)

## Performance Impact

### Network Latency
- kindnet: ~0.1ms pod-to-pod
- Calico: ~0.2-0.3ms (iptables processing)
- Cilium: ~0.15-0.2ms (eBPF is faster than iptables)

### Throughput
- kindnet: Near line-rate
- Calico: 5-10% overhead with policies
- Cilium: 3-5% overhead with policies

## Recommendations

1. **For minimal development** (no NetworkPolicy testing):
   - Stick with kindnet
   - Skip network isolation tests
   - Save 600MB-1GB RAM

2. **For NetworkPolicy testing**:
   - Use Calico (good balance)
   - +600MB RAM is manageable
   - Well-documented and stable

3. **For advanced networking** (L7 policies, observability):
   - Use Cilium
   - +1GB RAM cost
   - Better debugging tools

## Monitoring Resource Usage

```bash
# Check actual usage
kubectl top nodes
kubectl top pods -n kube-system
kubectl top pods -n calico-system
kubectl top pods -n cilium

# Watch resource usage
watch -n 2 'kubectl top pods -A | grep -E "(calico|cilium|kindnet)"'
```

## Configuration Options to Reduce Usage

### Calico
```yaml
# Disable unused features
apiVersion: operator.tigera.io/v1
kind: Installation
spec:
  # Disable Typha (saves ~200MB in small clusters)
  typhaEnabled: false
  # Reduce log verbosity
  logSeverityScreen: Warning
```

### Cilium
```bash
# Minimal installation
cilium install \
  --set hubble.enabled=false \
  --set operator.replicas=1 \
  --set ipam.mode=kubernetes
```