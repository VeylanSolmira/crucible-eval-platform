#!/bin/bash
# One-command deployment and EC2 update

set -e

echo "🚀 Crucible Platform - Deploy and Update"

# Deploy to S3
echo "📦 Deploying to S3..."
./scripts/deploy-to-s3.sh

# Get EC2 IP from Terraform
echo "🔍 Getting EC2 instance IP..."
EC2_IP=$(cd infrastructure/terraform && tofu output -raw eval_server_public_ip 2>/dev/null || echo "")

if [ -z "$EC2_IP" ]; then
    echo "❌ Could not get EC2 IP from Terraform outputs"
    echo "   Please run: cd infrastructure/terraform && tofu apply"
    exit 1
fi

# Get deployment details
BUCKET_NAME=$(cd infrastructure/terraform && tofu output -raw deployment_bucket_name)
VERSION=$(date +%Y%m%d-%H%M%S)
PACKAGE_NAME="crucible-platform-${VERSION}.tar.gz"

echo "📡 Updating EC2 instance at $EC2_IP..."

# Update the EC2 instance
ssh -o StrictHostKeyChecking=no ubuntu@$EC2_IP << EOF
set -e
echo "📥 Downloading latest package..."
cd /home/ubuntu
aws s3 cp s3://${BUCKET_NAME}/${PACKAGE_NAME} crucible-latest.tar.gz

echo "📂 Extracting package..."
rm -rf crucible-new
mkdir crucible-new
tar -xzf crucible-latest.tar.gz -C crucible-new

echo "🔄 Updating application..."
if [ -d crucible ]; then
    rm -rf crucible-old
    mv crucible crucible-old
fi
mv crucible-new crucible

echo "🔧 Restarting service..."
sudo systemctl restart crucible-platform

echo "✅ Update complete!"
echo ""
echo "Service status:"
sudo systemctl status crucible-platform --no-pager | head -n 10
EOF

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "1. Create SSH tunnel:"
echo "   ssh -L 8080:localhost:8080 ubuntu@$EC2_IP"
echo ""
echo "2. Access platform:"
echo "   http://localhost:8080"
echo ""
echo "3. View logs:"
echo "   ssh ubuntu@$EC2_IP 'sudo journalctl -u crucible-platform -f'"