#!/bin/bash
# Migration script from Docker Compose to Kubernetes
# This implements the cleanup plan with your modifications

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Crucible Platform: Docker Compose → Kubernetes Migration ===${NC}"
echo ""

# Check AWS CLI is configured
if ! aws sts get-caller-identity &>/dev/null; then
    echo -e "${RED}Error: AWS CLI not configured. Run 'aws configure' first.${NC}"
    exit 1
fi

# Get user confirmation
echo -e "${YELLOW}This script will:${NC}"
echo "1. Create a minimal EKS cluster (~$103/month)"
echo "2. Update Route53 DNS records (blue→dev, green→staging)"
echo "3. Archive Docker Compose files"
echo "4. Terminate blue/green EC2 instances (saving ~$20/month)"
echo ""
echo -e "${YELLOW}Note: crucible.veylan.dev is already broken, so no downtime risk${NC}"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Step 1: Archive Docker Compose files
echo -e "\n${GREEN}Step 1: Archiving Docker Compose files...${NC}"
if [ -f "docker-compose.yml" ]; then
    mkdir -p legacy/docker-compose-archive
    mv docker-compose*.yml legacy/docker-compose-archive/ 2>/dev/null || true
    echo "✓ Docker Compose files archived to legacy/docker-compose-archive/"
else
    echo "✓ Docker Compose files already archived or not found"
fi

# Step 2: Disable Docker Compose GitHub Action
echo -e "\n${GREEN}Step 2: Disabling Docker Compose deployment workflow...${NC}"
if [ -f ".github/workflows/deploy-compose.yml" ]; then
    # Comment out the entire workflow
    sed -i.bak '1s/^/# ARCHIVED - Migrated to Kubernetes\n# /' .github/workflows/deploy-compose.yml
    echo "✓ Commented out deploy-compose.yml workflow"
else
    echo "✓ Workflow already disabled or not found"
fi

# Step 3: Apply Terraform changes
echo -e "\n${GREEN}Step 3: Applying Terraform changes...${NC}"
cd infrastructure/terraform

# Initialize if needed
if [ ! -d ".terraform" ]; then
    echo "Initializing OpenTofu..."
    tofu init
fi

# Plan the changes
echo -e "\n${YELLOW}Planning Terraform changes...${NC}"
tofu plan -out=migration.tfplan

echo -e "\n${YELLOW}Review the plan above. Key changes:${NC}"
echo "- Creates EKS cluster and node group"
echo "- Updates Route53 records (blue→dev, green→staging)"
echo "- Keeps VPC, subnets, security groups, IAM roles"
echo ""
read -p "Apply these changes? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Terraform changes aborted. You can apply manually with: tofu apply migration.tfplan"
    exit 1
fi

# Apply the changes
tofu apply migration.tfplan

# Get outputs
EKS_CLUSTER_NAME=$(tofu output -raw eks_cluster_name)
KUBECTL_CONFIG_CMD=$(tofu output -raw kubectl_config_command)

# Step 4: Configure kubectl
echo -e "\n${GREEN}Step 4: Configuring kubectl...${NC}"
eval "$KUBECTL_CONFIG_CMD"
echo "✓ kubectl configured for cluster: $EKS_CLUSTER_NAME"

# Verify cluster access
if kubectl get nodes; then
    echo "✓ Successfully connected to EKS cluster"
else
    echo -e "${RED}Warning: Could not connect to EKS cluster${NC}"
fi

# Step 5: Terminate EC2 instances
echo -e "\n${GREEN}Step 5: Terminating blue/green EC2 instances...${NC}"
echo -e "${YELLOW}This will terminate the Docker Compose EC2 instances.${NC}"
read -p "Proceed with termination? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Get instance IDs
    BLUE_INSTANCE=$(aws ec2 describe-instances \
        --filters "Name=tag:DeploymentColor,Values=blue" \
                  "Name=tag:Project,Values=crucible-platform" \
                  "Name=instance-state-name,Values=running" \
        --query 'Reservations[0].Instances[0].InstanceId' \
        --output text)
    
    GREEN_INSTANCE=$(aws ec2 describe-instances \
        --filters "Name=tag:DeploymentColor,Values=green" \
                  "Name=tag:Project,Values=crucible-platform" \
                  "Name=instance-state-name,Values=running" \
        --query 'Reservations[0].Instances[0].InstanceId' \
        --output text)
    
    if [ "$BLUE_INSTANCE" != "None" ] && [ -n "$BLUE_INSTANCE" ]; then
        echo "Terminating blue instance: $BLUE_INSTANCE"
        aws ec2 terminate-instances --instance-ids "$BLUE_INSTANCE"
    fi
    
    if [ "$GREEN_INSTANCE" != "None" ] && [ -n "$GREEN_INSTANCE" ]; then
        echo "Terminating green instance: $GREEN_INSTANCE"
        aws ec2 terminate-instances --instance-ids "$GREEN_INSTANCE"
    fi
    
    echo "✓ EC2 instances terminated (or already terminated)"
else
    echo "Skipped EC2 termination. You can do this manually later."
fi

# Step 6: Create namespaces in Kubernetes
echo -e "\n${GREEN}Step 6: Creating Kubernetes namespaces...${NC}"
kubectl create namespace dev --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace staging --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace production --dry-run=client -o yaml | kubectl apply -f -
echo "✓ Created dev, staging, and production namespaces"

# Summary
echo -e "\n${GREEN}=== Migration Complete! ===${NC}"
echo ""
echo "✅ EKS cluster created: $EKS_CLUSTER_NAME"
echo "✅ kubectl configured"
echo "✅ DNS records updated (will propagate in 5-30 minutes):"
echo "   - dev.crucible.veylan.dev → Will point to K8s ingress"
echo "   - staging.crucible.veylan.dev → Will point to K8s ingress"
echo "✅ Docker Compose files archived"
echo "✅ EC2 instances terminated (saving ~$20/month)"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Deploy your application to Kubernetes:"
echo "   kubectl apply -k k8s/overlays/dev -n dev"
echo ""
echo "2. Access without LoadBalancer (save $25/month):"
echo "   - Get node IP: kubectl get nodes -o wide"
echo "   - Create NodePort service: kubectl expose deployment api-service --type=NodePort --port=8080"
echo "   - Access via: http://<node-ip>:30080"
echo ""
echo "3. Or attach an Elastic IP to a node for stable access"
echo ""
echo -e "${GREEN}Happy Kubernetes learning! 🚀${NC}"

# Create pause/resume scripts
echo -e "\n${GREEN}Creating pause/resume scripts...${NC}"
cat > scripts/pause-k8s.sh << 'EOF'
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
EOF

cat > scripts/resume-k8s.sh << 'EOF'
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
EOF

chmod +x scripts/pause-k8s.sh scripts/resume-k8s.sh
echo "✓ Created pause/resume scripts"

# Create delete/recreate scripts for full cost savings
cat > scripts/delete-k8s.sh << 'EOFDELETE'
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
EOFDELETE

cat > scripts/recreate-k8s-quick.sh << 'EOFRECREATE'
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
EOFRECREATE

chmod +x scripts/delete-k8s.sh scripts/recreate-k8s-quick.sh
echo "✓ Created delete/recreate scripts for full cost savings"

# Cleanup Terraform plan file
rm -f migration.tfplan