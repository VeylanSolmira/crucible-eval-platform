#!/bin/bash
set -euo pipefail

# Verify gVisor installation on EKS nodes

echo "🔍 Verifying gVisor installation..."
echo ""

# Check if RuntimeClass exists
echo "1️⃣ Checking RuntimeClass..."
if kubectl get runtimeclass gvisor &>/dev/null; then
    echo "✅ RuntimeClass 'gvisor' exists"
    kubectl get runtimeclass gvisor
else
    echo "❌ RuntimeClass 'gvisor' not found"
fi
echo ""

# Check DaemonSet status
echo "2️⃣ Checking gVisor installer DaemonSet..."
kubectl get daemonset -n crucible gvisor-installer || echo "❌ DaemonSet not found"
echo ""

# Check installer pods
echo "3️⃣ Checking installer pods..."
kubectl get pods -n crucible -l app=gvisor-installer
echo ""

# Get logs from all installer pods
echo "4️⃣ Installation logs from all nodes:"
for pod in $(kubectl get pods -n crucible -l app=gvisor-installer -o jsonpath='{.items[*].metadata.name}'); do
    node=$(kubectl get pod "$pod" -n crucible -o jsonpath='{.spec.nodeName}')
    echo "--- Node: $node (Pod: $pod) ---"
    kubectl logs "$pod" -n crucible -c gvisor-installer 2>/dev/null | tail -20 || echo "No logs available"
    echo ""
done

# Test gVisor with a simple pod
echo "5️⃣ Testing gVisor runtime..."
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: gvisor-test
  namespace: default
spec:
  runtimeClassName: gvisor
  containers:
  - name: test
    image: busybox
    command: ["sh", "-c", "echo 'gVisor test successful!' && uname -a && sleep 5"]
  restartPolicy: Never
EOF

echo "⏳ Waiting for test pod..."
kubectl wait --for=condition=Ready pod/gvisor-test --timeout=30s 2>/dev/null || true

echo ""
echo "📋 Test pod status:"
kubectl get pod gvisor-test
kubectl logs gvisor-test 2>/dev/null || echo "No logs yet"

echo ""
echo "🧹 Cleaning up test pod..."
kubectl delete pod gvisor-test --wait=false

echo ""
echo "✅ Verification complete!"
echo ""
echo "If gVisor is working correctly, you should see:"
echo "  - RuntimeClass exists"
echo "  - DaemonSet is running on all nodes"
echo "  - Installation logs show 'SUCCESS'"
echo "  - Test pod runs with 'gVisor test successful!'"