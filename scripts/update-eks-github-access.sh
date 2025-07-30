#!/bin/bash
# Update EKS cluster to allow GitHub Actions IP ranges

set -e

CLUSTER_NAME="crucible-platform"
REGION="us-west-2"

echo "Fetching GitHub Actions IP ranges..."
GITHUB_IPS=$(curl -s https://api.github.com/meta | jq -r '.actions[]' | head -100)  # Limiting to first 100 due to AWS API limits

# Convert to JSON array format
IP_ARRAY="["
first=true
while IFS= read -r ip; do
    if [ "$first" = true ]; then
        IP_ARRAY="$IP_ARRAY\"$ip\""
        first=false
    else
        IP_ARRAY="$IP_ARRAY,\"$ip\""
    fi
done <<< "$GITHUB_IPS"
IP_ARRAY="$IP_ARRAY]"

echo "Updating EKS cluster access..."
aws eks update-cluster-config \
    --name "$CLUSTER_NAME" \
    --region "$REGION" \
    --resources-vpc-config endpointPublicAccess=true,publicAccessCidrs="$IP_ARRAY"

echo "EKS cluster access updated. Waiting for update to complete..."
aws eks wait cluster-active --name "$CLUSTER_NAME" --region "$REGION"

echo "Done! GitHub Actions can now access the EKS cluster."