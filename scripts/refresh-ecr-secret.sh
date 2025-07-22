#!/bin/bash
# Refresh ECR secret for Kubernetes
# ECR tokens expire after 12 hours, so this needs to be run periodically

set -e

NAMESPACE=${NAMESPACE:-crucible}
REGION=${AWS_REGION:-us-west-2}
REGISTRY=${ECR_REGISTRY:-503132503803.dkr.ecr.us-west-2.amazonaws.com}

echo "🔄 Refreshing ECR secret in namespace: $NAMESPACE"

# Delete existing secret if it exists
kubectl delete secret ecr-secret -n $NAMESPACE 2>/dev/null || true

# Get fresh ECR password
echo "🔑 Getting fresh ECR authentication token..."
ECR_PASSWORD=$(aws ecr get-login-password --region $REGION)

# Create new secret
echo "🔐 Creating Kubernetes secret..."
kubectl create secret docker-registry ecr-secret \
  --docker-server="$REGISTRY" \
  --docker-username=AWS \
  --docker-password="$ECR_PASSWORD" \
  -n $NAMESPACE

echo "✅ ECR secret refreshed successfully!"
echo "   Registry: $REGISTRY"
echo "   Namespace: $NAMESPACE"
echo "   Valid for: 12 hours"

# Verify the secret was created correctly
if kubectl get secret ecr-secret -n $NAMESPACE >/dev/null 2>&1; then
    echo "✅ Secret verified"
else
    echo "❌ Failed to verify secret"
    exit 1
fi