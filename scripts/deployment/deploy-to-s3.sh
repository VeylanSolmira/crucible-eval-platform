#!/bin/bash
# Deploy Crucible Platform to S3 for EC2 pickup
# Note: S3 bucket must be created via Terraform first

set -e

# Configuration - get bucket name from environment, SSM, or Terraform
if [ -z "$DEPLOYMENT_BUCKET" ]; then
    # Try to get from SSM parameter (works in GitHub Actions)
    BUCKET_NAME=$(aws ssm get-parameter --name "/crucible/deployment-bucket" --query 'Parameter.Value' --output text 2>/dev/null || echo "")
    
    if [ -z "$BUCKET_NAME" ]; then
        # Try to get from Terraform output (works locally)
        BUCKET_NAME=$(cd infrastructure/terraform && tofu output -raw deployment_bucket_name 2>/dev/null || echo "")
    fi
    
    if [ -z "$BUCKET_NAME" ]; then
        echo "❌ Error: Could not determine deployment bucket"
        echo "   Options:"
        echo "   1. Set environment: export DEPLOYMENT_BUCKET=<bucket-name>"
        echo "   2. Ensure SSM parameter exists: /crucible/deployment-bucket"
        echo "   3. Run from terraform dir: cd infrastructure/terraform"
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
TEMP_DIR="/tmp/crucible-deploy-${VERSION}"

# Create clean copy using rsync with .deployignore
echo "   Copying files..."
mkdir -p "${TEMP_DIR}"

# Use rsync to copy files, respecting .deployignore
if [ -f .deployignore ]; then
    rsync -av --exclude-from=.deployignore . "${TEMP_DIR}/"
else
    # Fallback to basic excludes if .deployignore missing
    rsync -av \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='venv' \
        --exclude='.env' \
        --exclude='*.log' \
        . "${TEMP_DIR}/"
fi

# Create tarball from clean copy
echo "   Creating archive..."
tar -czf "/tmp/${PACKAGE_NAME}" -C "${TEMP_DIR}" .

# Cleanup temp directory
rm -rf "${TEMP_DIR}"

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