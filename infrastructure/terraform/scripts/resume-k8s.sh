#!/bin/bash
# Resume Kubernetes cluster

CLUSTER_NAME="crucible-platform"
NODEGROUP_NAME="crucible-platform-workers"

echo "▶️ Resuming Kubernetes cluster..."

# Scale node group back to 2 nodes
aws eks update-nodegroup-config \
  --cluster-name $CLUSTER_NAME \
  --nodegroup-name $NODEGROUP_NAME \
  --scaling-config minSize=1,maxSize=3,desiredSize=2

echo "⏳ Waiting for nodes to be ready (this may take 5 minutes)..."
sleep 30
kubectl wait --for=condition=Ready nodes --all --timeout=300s || true

echo "✅ Cluster resumed!"
kubectl get nodes
