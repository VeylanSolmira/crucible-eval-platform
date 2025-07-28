#!/bin/bash
# Pause Kubernetes cluster to save costs (~$90/month)

CLUSTER_NAME="crucible-platform"
NODEGROUP_NAME="crucible-platform-workers"

echo "🛑 Pausing Kubernetes cluster..."

# Scale node group to 0
aws eks update-nodegroup-config \
  --cluster-name $CLUSTER_NAME \
  --nodegroup-name $NODEGROUP_NAME \
  --scaling-config minSize=0,maxSize=3,desiredSize=0

echo "✅ Cluster paused. You're now only paying for the control plane ($73/month)"
echo "💡 Run ./scripts/resume-k8s.sh to resume"
