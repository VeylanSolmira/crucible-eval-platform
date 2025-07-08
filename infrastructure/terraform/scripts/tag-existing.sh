#!/bin/bash
# Script to tag existing infrastructure as "blue" without recreation

echo "This script will tag your existing infrastructure as 'blue' deployment"
echo "No resources will be recreated - only tags will be added/updated"
echo ""
echo "Current deployment will be tagged as:"
echo "  - DeploymentColor: blue"
echo "  - DeploymentVersion: 1.0"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Running terraform plan..."
    PLAN_OUTPUT=$(tofu plan -var="deployment_color=blue" -var="deployment_version=1.0" -no-color 2>&1)
    echo "$PLAN_OUTPUT"
    
    # Check for any resources being created, destroyed, or replaced
    if echo "$PLAN_OUTPUT" | grep -E "will be created|will be destroyed|must be replaced|will be replaced" > /dev/null; then
        echo ""
        echo "❌ ERROR: This operation would create, destroy, or replace resources!"
        echo "This script is only for adding tags to existing resources."
        echo "Aborting for safety."
        exit 1
    fi
    
    # Check if only tag updates
    if echo "$PLAN_OUTPUT" | grep -E "~ update in-place|~ resource \"aws_instance\"" > /dev/null; then
        echo ""
        echo "✅ Plan looks safe - only tag updates detected."
        echo ""
        read -p "Apply these tag changes? (y/n) " -n 1 -r
        echo ""
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            tofu apply -var="deployment_color=blue" -var="deployment_version=1.0" -auto-approve
            echo ""
            echo "✅ Existing infrastructure tagged as blue deployment!"
            echo ""
            echo "To verify tags:"
            echo "aws ec2 describe-instances --instance-ids \$(tofu output -raw instance_id 2>/dev/null) --query 'Reservations[0].Instances[0].Tags' --output table"
        else
            echo "Cancelled."
        fi
    else
        echo ""
        echo "⚠️  No changes detected. Your infrastructure may already be tagged."
    fi
else
    echo "Cancelled."
fi