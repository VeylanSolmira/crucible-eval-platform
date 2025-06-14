#!/bin/bash
# Deploy Crucible Platform to S3 for EC2 pickup
# Note: S3 bucket must be created via Terraform first

set -e

# Configuration - get bucket name from Terraform output or environment
if [ -z "$DEPLOYMENT_BUCKET" ]; then
    # Try to get from Terraform output
    BUCKET_NAME=$(cd infrastructure/terraform && tofu output -raw deployment_bucket_name 2>/dev/null || echo "")
    if [ -z "$BUCKET_NAME" ]; then
        echo "❌ Error: DEPLOYMENT_BUCKET not set and could not get from Terraform"
        echo "   Run: export DEPLOYMENT_BUCKET=<your-bucket-name>"
        echo "   Or: cd infrastructure/terraform && tofu apply"
        exit 1
    fi
else
    BUCKET_NAME="$DEPLOYMENT_BUCKET"
fi

AWS_REGION="${AWS_REGION:-us-west-2}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
VERSION="${VERSION:-${TIMESTAMP}}"

echo "🚀 Deploying Crucible Platform to S3"
echo "   Bucket: $BUCKET_NAME"
echo "   Version: $VERSION"

# Verify bucket exists (created by Terraform)
if ! aws s3 ls "s3://${BUCKET_NAME}" >/dev/null 2>&1; then
    echo "❌ Error: Bucket $BUCKET_NAME does not exist"
    echo "   Please run: cd infrastructure/terraform && tofu apply"
    exit 1
fi

# Create deployment package
echo "📦 Creating deployment package..."
PACKAGE_NAME="crucible-platform-${VERSION}.tar.gz"

# Files to include
tar -czf "/tmp/${PACKAGE_NAME}" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='venv' \
    --exclude='env' \
    --exclude='.pytest_cache' \
    --exclude='logs' \
    --exclude='*.log' \
    --exclude='docs' \
    --exclude='.docker' \
    --exclude='**/.terraform' \
    --exclude='*.tar' \
    --exclude='*.tar.gz' \
    --exclude='*.zip' \
    --exclude='.DS_Store' \
    --exclude='node_modules' \
    --exclude='*.db' \
    --exclude='*.sqlite' \
    --exclude='tmp/*' \
    --exclude='temp/*' \
    .

# Upload to S3
echo "⬆️  Uploading to S3..."
aws s3 cp "/tmp/${PACKAGE_NAME}" "s3://${BUCKET_NAME}/${PACKAGE_NAME}"

# Update latest pointer
echo "${VERSION}" > /tmp/latest-version.txt
aws s3 cp /tmp/latest-version.txt "s3://${BUCKET_NAME}/latest-version.txt"

# Set up SSM parameter for version tracking
echo "📝 Updating SSM parameter..."
aws ssm put-parameter \
    --name "/crucible/current-version" \
    --value "${VERSION}" \
    --type "String" \
    --overwrite \
    --region "${AWS_REGION}" 2>/dev/null || true

# Clean up
rm -f "/tmp/${PACKAGE_NAME}" /tmp/latest-version.txt

echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "1. Update Terraform variables:"
echo "   deployment_bucket = \"${BUCKET_NAME}\""
echo "   deployment_key = \"${PACKAGE_NAME}\""
echo ""
echo "2. Deploy infrastructure:"
echo "   cd infrastructure/terraform"
echo "   tofu apply"
echo ""
echo "3. SSH tunnel to access:"
echo "   ssh -L 8080:localhost:8080 ubuntu@<ec2-ip>"
echo "   Then browse to http://localhost:8080"