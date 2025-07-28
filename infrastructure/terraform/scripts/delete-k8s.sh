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

# Quick backup
mkdir -p $BACKUP_DIR
for ns in $(kubectl get ns -o name | grep -v "kube-\|default" | cut -d/ -f2); do
    kubectl get all,cm,secrets -n $ns -o yaml > "$BACKUP_DIR/$ns-resources.yaml" 2>/dev/null || true
done
tar -czf "k8s-backup-$(date +%Y%m%d-%H%M%S).tar.gz" -C k8s-backups "$(basename $BACKUP_DIR)"

# Delete cluster
echo "Deleting cluster (10-15 minutes)..."
if command -v eksctl &> /dev/null; then
    eksctl delete cluster --name $CLUSTER_NAME --wait
else
    aws eks delete-cluster --name $CLUSTER_NAME
fi

echo -e "${GREEN}✅ Cluster deleted! Saving \$73/month!${NC}"
