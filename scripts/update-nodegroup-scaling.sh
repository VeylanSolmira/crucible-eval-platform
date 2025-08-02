#!/bin/bash
# Update EKS nodegroup to allow scaling between 1-2 nodes

set -e

CLUSTER_NAME="crucible-platform"
REGION="us-west-2"

echo "Getting nodegroup name..."
NODEGROUP=$(aws eks list-nodegroups --cluster-name $CLUSTER_NAME --region $REGION --query 'nodegroups[0]' --output text)

if [ -z "$NODEGROUP" ]; then
    echo "Error: No nodegroup found for cluster $CLUSTER_NAME"
    exit 1
fi

echo "Found nodegroup: $NODEGROUP"

echo "Current scaling configuration:"
aws eks describe-nodegroup --cluster-name $CLUSTER_NAME --nodegroup-name $NODEGROUP --region $REGION \
    --query 'nodegroup.scalingConfig' --output table

echo ""
echo "Updating nodegroup to allow 1-2 nodes..."
aws eks update-nodegroup-config \
    --cluster-name $CLUSTER_NAME \
    --nodegroup-name $NODEGROUP \
    --region $REGION \
    --scaling-config minSize=1,maxSize=2,desiredSize=1

echo ""
echo "Waiting for update to complete..."
aws eks wait nodegroup-active \
    --cluster-name $CLUSTER_NAME \
    --nodegroup-name $NODEGROUP \
    --region $REGION

echo ""
echo "Updated scaling configuration:"
aws eks describe-nodegroup --cluster-name $CLUSTER_NAME --nodegroup-name $NODEGROUP --region $REGION \
    --query 'nodegroup.scalingConfig' --output table

echo ""
echo "Tagging Auto Scaling Group for cluster-autoscaler..."
ASG_NAME=$(aws eks describe-nodegroup --cluster-name $CLUSTER_NAME --nodegroup-name $NODEGROUP --region $REGION \
    --query 'nodegroup.resources.autoScalingGroups[0].name' --output text)

if [ -n "$ASG_NAME" ]; then
    echo "Found ASG: $ASG_NAME"
    
    # Add tags required by cluster-autoscaler
    aws autoscaling create-or-update-tags --region $REGION --tags \
        "ResourceId=$ASG_NAME,ResourceType=auto-scaling-group,Key=k8s.io/cluster-autoscaler/enabled,Value=true,PropagateAtLaunch=false" \
        "ResourceId=$ASG_NAME,ResourceType=auto-scaling-group,Key=k8s.io/cluster-autoscaler/$CLUSTER_NAME,Value=owned,PropagateAtLaunch=false"
    
    echo "Tags added successfully"
else
    echo "Warning: Could not find Auto Scaling Group"
fi

echo ""
echo "✅ Nodegroup updated to support 1-2 node scaling"