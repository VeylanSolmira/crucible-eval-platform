#!/bin/bash
# Recreate EKS cluster from scratch

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== EKS Cluster Recreation Script ===${NC}"
echo ""

# Check if cluster already exists
if aws eks describe-cluster --name crucible-platform &>/dev/null; then
    echo -e "${YELLOW}Cluster already exists! Use this script only after deletion.${NC}"
    exit 1
fi

echo "This script will:"
echo "1. Create a new EKS cluster (~$73/month)"
echo "2. Set up 2 worker nodes (~$30/month)"  
echo "3. Configure kubectl"
echo "4. Restore your applications from Git"
echo ""
echo -e "${YELLOW}Total time: ~20-25 minutes${NC}"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Step 1: Create cluster with Terraform
echo -e "\n${GREEN}Step 1: Creating EKS cluster with OpenTofu...${NC}"
cd infrastructure/terraform

# Check for required Terraform files
if [ ! -f "eks-minimal.tf" ]; then
    echo -e "${RED}Error: eks-minimal.tf not found!${NC}"
    echo "Please ensure you're in the correct directory."
    exit 1
fi

# Initialize OpenTofu if needed
if [ ! -d ".terraform" ]; then
    echo "Initializing OpenTofu..."
    tofu init
fi

# Apply Terraform
echo -e "${YELLOW}Creating cluster (this will take 15-20 minutes)...${NC}"
tofu apply -auto-approve -target=aws_eks_cluster.main -target=aws_eks_node_group.main

# Get cluster name
CLUSTER_NAME=$(tofu output -raw eks_cluster_name)
cd ../..

# Step 2: Configure kubectl
echo -e "\n${GREEN}Step 2: Configuring kubectl...${NC}"
aws eks update-kubeconfig --region us-west-2 --name $CLUSTER_NAME

# Verify connection
echo "Verifying cluster connection..."
kubectl get nodes

# Step 3: Create namespaces
echo -e "\n${GREEN}Step 3: Creating namespaces...${NC}"
kubectl create namespace dev --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace staging --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace production --dry-run=client -o yaml | kubectl apply -f -

# Step 4: Deploy applications from Git
echo -e "\n${GREEN}Step 4: Deploying applications...${NC}"

# Check if k8s manifests exist
if [ -d "k8s/overlays/dev" ]; then
    echo "Deploying to dev namespace..."
    kubectl apply -k k8s/overlays/dev -n dev
else
    echo -e "${YELLOW}No k8s/overlays/dev found. Skipping app deployment.${NC}"
fi

# Step 5: Restore from backup (if exists)
echo -e "\n${GREEN}Step 5: Checking for backups...${NC}"
LATEST_BACKUP=$(ls -t k8s-backup-*.tar.gz 2>/dev/null | head -1)

if [ -n "$LATEST_BACKUP" ]; then
    echo -e "${YELLOW}Found backup: $LATEST_BACKUP${NC}"
    read -p "Restore from this backup? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Extract backup
        RESTORE_DIR="restore-$(date +%Y%m%d-%H%M%S)"
        mkdir -p $RESTORE_DIR
        tar -xzf "$LATEST_BACKUP" -C "$RESTORE_DIR"
        
        # Apply resources
        for file in $RESTORE_DIR/*/dev-resources.yaml $RESTORE_DIR/*/staging-resources.yaml $RESTORE_DIR/*/production-resources.yaml; do
            if [ -f "$file" ]; then
                echo "Restoring: $(basename $file)"
                kubectl apply -f "$file" || true
            fi
        done
        
        # Cleanup
        rm -rf $RESTORE_DIR
        echo -e "${GREEN}✓ Backup restored${NC}"
    fi
else
    echo "No backups found. Starting fresh!"
fi

# Step 6: Set up ingress (optional)
echo -e "\n${GREEN}Step 6: Setting up access...${NC}"
echo "To avoid LoadBalancer costs, using NodePort:"

# Get a node external IP
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}')
if [ -z "$NODE_IP" ]; then
    NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
    echo -e "${YELLOW}Note: Nodes only have internal IPs. You'll need to access via SSH tunnel.${NC}"
fi

echo ""
echo -e "${GREEN}=== Cluster Recreation Complete! ===${NC}"
echo ""
echo "✅ Cluster name: $CLUSTER_NAME"
echo "✅ Nodes: $(kubectl get nodes --no-headers | wc -l)"
echo "✅ Namespaces: dev, staging, production"
echo ""
echo "📍 Access your services:"
if [ -n "$NODE_IP" ]; then
    echo "   Node IP: $NODE_IP"
    echo "   NodePort: 30080-32767"
else
    echo "   Set up SSH tunnel to access services"
fi
echo ""
echo "💡 Quick commands:"
echo "   kubectl get pods -A"
echo "   kubectl port-forward svc/api-service 8080:8080 -n dev"
echo "   ./scripts/pause-k8s.sh  # Save money when not using"
echo ""
echo "💰 Remember: You're now spending $103/month. Delete when not using!"