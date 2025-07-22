# Network Isolation Limitations in Development

## Issue

The default Kind installation uses `kindnet` CNI, which does **not** support NetworkPolicy enforcement. This means:

1. NetworkPolicy resources are accepted but not enforced
2. Evaluation pods can make network connections even with deny-all policies
3. Network isolation tests will fail

## Production vs Development

### Production Environment
- Uses a proper CNI (AWS VPC CNI, Calico, Cilium) that enforces NetworkPolicy
- Has gVisor runtime for additional isolation
- Full network isolation is enforced

### Development Environment (macOS)
- Kind uses kindnet CNI (no NetworkPolicy support)
- gVisor is not available on macOS hosts
- Network isolation relies only on NetworkPolicy (which isn't enforced)

## Solutions

### Option 1: Install Calico (Recommended for Testing)
```bash
# Delete current cluster
kind delete cluster --name crucible

# Create cluster without default CNI
kind create cluster --config k8s/kind-with-calico.yaml --name crucible

# Install Calico
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/tigera-operator.yaml
kubectl apply -f k8s/calico-config.yaml

# Wait for Calico
kubectl -n calico-system wait --for=condition=ready pod --all --timeout=300s

# Redeploy application
skaffold run
```

### Option 2: Skip Network Tests in Development
```python
@pytest.mark.skipif(
    os.getenv("SKIP_NETWORK_ISOLATION_TESTS", "false").lower() == "true",
    reason="Network isolation not available in development"
)
def test_network_isolation():
    ...
```

### Option 3: Use Test Markers
```bash
# Run all tests except network isolation
pytest -m "not network_isolation"

# Only run if CNI supports NetworkPolicy
pytest -m "network_isolation" --network-policy-enforced
```

## Checking CNI Support

```bash
# Check which CNI is installed
kubectl get pods -n kube-system | grep -E "(calico|cilium|weave|flannel|kindnet)"

# Test if NetworkPolicy is enforced
kubectl apply -f tests/network-policy-test.yaml
kubectl exec test-pod -- curl -m 2 http://google.com
```

## Resource Considerations

- **Calico**: ~200MB RAM per node, ~100MB disk
- **Cilium**: ~300MB RAM per node, ~150MB disk  
- **kindnet**: ~50MB RAM per node (but no NetworkPolicy)

## Recommendation

For development on macOS:
1. Accept the limitation and skip network isolation tests
2. Document that network isolation is not tested locally
3. Ensure CI/CD tests network isolation in a proper environment
4. If network development is critical, use Calico or Cilium despite resource overhead