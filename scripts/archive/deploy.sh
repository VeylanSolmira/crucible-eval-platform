#!/bin/bash
# Deploy infrastructure with Terraform

set -e

echo "🚀 Deploying Crucible Platform Infrastructure..."

# Check for AWS credentials
if ! aws sts get-caller-identity &>/dev/null; then
    echo "❌ AWS credentials not configured. Run 'aws configure' first."
    exit 1
fi

# Check for terraform
if ! command -v terraform &>/dev/null; then
    echo "❌ Terraform not found. Please install Terraform first."
    exit 1
fi

# Terraform will automatically package Lambda from src/lambda/

# Initialize Terraform
echo "🔧 Initializing Terraform..."
terraform init

# Show the plan
echo "📋 Planning infrastructure changes..."
terraform plan

# Ask for confirmation
echo ""
read -p "Deploy these changes? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🏗️  Deploying infrastructure..."
    terraform apply -auto-approve
    
    echo ""
    echo "✅ Deployment complete!"
    echo ""
    echo "📌 Important outputs:"
    echo "-------------------"
    
    # Show outputs
    if terraform output &>/dev/null; then
        echo "EC2 Server: $(terraform output -raw eval_server_public_ip 2>/dev/null || echo 'Not deployed')"
        echo "SSH Command: $(terraform output -raw ssh_command 2>/dev/null || echo 'Not available')"
        echo "Platform URL: $(terraform output -raw platform_url 2>/dev/null || echo 'Not available')"
        echo "API Endpoint: $(terraform output -raw api_endpoint 2>/dev/null || echo 'Not deployed')"
    fi
    
    echo ""
    echo "🔐 Next steps:"
    echo "1. SSH to server: ssh ubuntu@$(terraform output -raw eval_server_public_ip 2>/dev/null || echo '<IP>')"
    echo "2. Clone your repo and test gVisor"
    echo "3. Run: python extreme_mvp_gvisor.py"
else
    echo "❌ Deployment cancelled"
fi