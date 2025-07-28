#!/bin/bash
# Delete EKS cluster to save $73/month

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

CLUSTER_NAME="crucible-platform"
BACKUP_DIR="k8s-backups/$(date +%Y%m%d-%H%M%S)"

echo -e "${YELLOW}=== EKS Cluster Deletion Script ===${NC}"
echo -e "${YELLOW}This will save you \$73/month while cluster is deleted${NC}"
echo ""

# Check if cluster exists
if ! aws eks describe-cluster --name $CLUSTER_NAME &>/dev/null; then
    echo -e "${YELLOW}Cluster $CLUSTER_NAME not found. Nothing to delete.${NC}"
    exit 0
fi

echo "This script will:"
echo "1. Backup current Kubernetes state"
echo "2. Delete the EKS cluster (saves $73/month)"
echo "3. Keep all your code, images, and infrastructure"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Step 1: Quick backup of deployed resources
echo -e "\n${GREEN}Step 1: Backing up Kubernetes state...${NC}"
mkdir -p $BACKUP_DIR

# Get all resources from non-system namespaces
for ns in $(kubectl get ns -o name | grep -v "kube-\|default" | cut -d/ -f2); do
    echo "Backing up namespace: $ns"
    kubectl get all,cm,secrets,ingress -n $ns -o yaml > "$BACKUP_DIR/$ns-resources.yaml" 2>/dev/null || true
done

# Save cluster info for reference
echo "Saving cluster configuration..."
aws eks describe-cluster --name $CLUSTER_NAME > "$BACKUP_DIR/cluster-config.json"
kubectl config view --minify --flatten > "$BACKUP_DIR/kubeconfig.yaml"

# Compress backup
tar -czf "k8s-backup-$(date +%Y%m%d-%H%M%S).tar.gz" -C k8s-backups "$(basename $BACKUP_DIR)"
echo -e "${GREEN}✓ Backup saved to: k8s-backup-$(date +%Y%m%d-%H%M%S).tar.gz${NC}"

# Step 2: Delete node group first (faster)
echo -e "\n${GREEN}Step 2: Deleting node group...${NC}"
NODEGROUP=$(aws eks list-nodegroups --cluster-name $CLUSTER_NAME --query 'nodegroups[0]' --output text)
if [ "$NODEGROUP" != "None" ] && [ -n "$NODEGROUP" ]; then
    aws eks delete-nodegroup --cluster-name $CLUSTER_NAME --nodegroup-name $NODEGROUP
    echo "Waiting for node group deletion..."
    aws eks wait nodegroup-deleted --cluster-name $CLUSTER_NAME --nodegroup-name $NODEGROUP 2>/dev/null || true
fi

# Step 3: Delete cluster
echo -e "\n${GREEN}Step 3: Deleting EKS cluster...${NC}"
echo "This will take 10-15 minutes..."

# Option 1: If using eksctl
if command -v eksctl &> /dev/null; then
    eksctl delete cluster --name $CLUSTER_NAME --wait
else
    # Option 2: Using AWS CLI (requires manual cleanup of some resources)
    aws eks delete-cluster --name $CLUSTER_NAME
    
    echo "Waiting for cluster deletion..."
    while aws eks describe-cluster --name $CLUSTER_NAME &>/dev/null; do
        echo -n "."
        sleep 30
    done
fi

echo -e "\n${GREEN}✅ Cluster deleted successfully!${NC}"

# Summary
echo -e "\n${GREEN}=== Deletion Complete ===${NC}"
echo ""
echo "💰 You're now saving $73/month!"
echo "📦 Your backup is in: k8s-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
echo "🚀 To recreate cluster, run: ./scripts/recreate-k8s.sh"
echo ""
echo "What's preserved:"
echo "✓ All your code (in Git)"
echo "✓ Container images (in ECR)"
echo "✓ VPC and networking"
echo "✓ IAM roles and policies"
echo "✓ Your sanity and wallet 😄"