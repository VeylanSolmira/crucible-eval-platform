#!/bin/bash
# Update Crucible Platform from S3
# This script is called by GitHub Actions after deployment

set -e

# Get deployment bucket from SSM or environment
BUCKET_NAME=$(aws ssm get-parameter --name "/crucible/deployment-bucket" --query 'Parameter.Value' --output text 2>/dev/null || echo "")
if [ -z "$BUCKET_NAME" ]; then
    echo "Error: Could not get deployment bucket from SSM"
    exit 1
fi

# Get latest version
LATEST_VERSION=$(aws s3 cp s3://${BUCKET_NAME}/latest-version.txt - 2>/dev/null || echo "")
if [ -z "$LATEST_VERSION" ]; then
    echo "Error: Could not get latest version"
    exit 1
fi

echo "Updating to version: $LATEST_VERSION"

# Download and extract
cd /home/ubuntu
aws s3 cp s3://${BUCKET_NAME}/crucible-platform-${LATEST_VERSION}.tar.gz /tmp/
tar -xzf /tmp/crucible-platform-${LATEST_VERSION}.tar.gz -C /home/ubuntu/crucible --strip-components=1

# Update dependencies
cd /home/ubuntu/crucible
./venv/bin/pip install -r requirements.txt
./venv/bin/pip install -e .

# Update systemd service if changed
if ! diff -q /home/ubuntu/crucible/infrastructure/systemd/crucible-platform.service /etc/systemd/system/crucible-platform.service; then
    echo "Updating systemd service file"
    sudo cp /home/ubuntu/crucible/infrastructure/systemd/crucible-platform.service /etc/systemd/system/
    sudo systemctl daemon-reload
fi

# Restart service
sudo systemctl restart crucible-platform

# Cleanup
rm -f /tmp/crucible-platform-${LATEST_VERSION}.tar.gz

echo "Update complete!"