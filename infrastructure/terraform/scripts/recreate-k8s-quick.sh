#!/bin/bash
# Quick recreate - just the essentials

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Quick EKS Recreation ===${NC}"

# Create with OpenTofu
cd infrastructure/terraform
tofu apply -auto-approve -target=aws_eks_cluster.main -target=aws_eks_node_group.main
cd ../..

# Configure kubectl
aws eks update-kubeconfig --region us-west-2 --name crucible-platform

# Create namespaces and deploy
kubectl create namespace dev --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -k k8s/overlays/dev -n dev || true

echo -e "${GREEN}✅ Cluster ready in ~20 minutes!${NC}"
