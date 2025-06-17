#!/bin/bash
# Pull-based container updater
# Can be run by cron every 5 minutes or systemd timer

set -e

ECR_REPO="${ECR_REPOSITORY_URL}"
SERVICE_NAME="crucible-docker"

# Login to ECR
/usr/local/bin/docker-ecr-login

# Check if there's a newer image
echo "Checking for updates..."
CURRENT_IMAGE=$(docker inspect crucible-platform 2>/dev/null | jq -r '.[0].Image' || echo "none")
docker pull ${ECR_REPO}:latest > /tmp/docker-pull.log 2>&1
NEW_IMAGE=$(docker inspect ${ECR_REPO}:latest | jq -r '.[0].Id')

if [ "$CURRENT_IMAGE" != "$NEW_IMAGE" ]; then
    echo "New image detected! Current: $CURRENT_IMAGE, New: $NEW_IMAGE"
    echo "Restarting service..."
    
    # Restart the service (systemd will handle the container update)
    systemctl restart $SERVICE_NAME
    
    # Log the update
    echo "[$(date)] Updated from $CURRENT_IMAGE to $NEW_IMAGE" >> /var/log/crucible/updates.log
else
    echo "No update needed. Current image is up to date."
fi