#!/bin/bash
set -e

# Log all output
exec > >(tee -a /var/log/userdata.log)
exec 2>&1

# Update system
apt-get update
apt-get upgrade -y

# Install Docker
apt-get install -y \
  ca-certificates \
  curl \
  gnupg \
  lsb-release

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io

# Install gVisor
curl -fsSL https://gvisor.dev/archive.key | apt-key add -
add-apt-repository "deb https://storage.googleapis.com/gvisor/releases release main"
apt-get update
apt-get install -y runsc

# Configure Docker to use runsc
runsc install
systemctl restart docker

# Add ubuntu user to docker group
usermod -aG docker ubuntu

# Install Python 3.11
apt-get install -y python3.11 python3.11-venv python3-pip

# Install git and additional tools
apt-get install -y git jq awscli

# Create application directory structure
mkdir -p /home/ubuntu/crucible
mkdir -p /var/log/crucible
chown -R ubuntu:ubuntu /home/ubuntu/crucible /var/log/crucible

# Register this instance as ready for deployment
INSTANCE_ID=$(ec2-metadata --instance-id | cut -d " " -f 2)
aws ssm put-parameter \
    --name "/crucible/instances/${INSTANCE_ID}/status" \
    --value "ready" \
    --type "String" \
    --overwrite 2>/dev/null || true

# Store deployment bucket name if provided
if [ -n "${deployment_bucket}" ]; then
    aws ssm put-parameter \
        --name "/crucible/instances/${INSTANCE_ID}/deployment-bucket" \
        --value "${deployment_bucket}" \
        --type "String" \
        --overwrite 2>/dev/null || true
fi

# Create deployment instructions
cat > /home/ubuntu/deployment-instructions.txt <<EOF
=== Crucible Platform Deployment Instructions ===

This EC2 instance is ready for deployment but has NO APPLICATION CODE.
Following the Kubernetes pattern: infrastructure is ready, code deployment is separate.

To deploy the application:

1. From GitHub Actions (Recommended):
   - Go to: https://github.com/YOUR_ORG/YOUR_REPO/actions
   - Click "Deploy to EC2" workflow
   - Click "Run workflow" button
   - Select branch: main

2. From GitHub CLI:
   gh workflow run deploy.yml

3. From AWS CLI (after first deployment):
   aws ssm send-command \\
     --instance-ids $(ec2-metadata --instance-id | cut -d " " -f 2) \\
     --document-name "AWS-RunShellScript" \\
     --parameters 'commands=["/home/ubuntu/update-platform.sh"]'

Instance Status:
- Infrastructure: ✅ Ready
- Application: ⏳ Awaiting deployment
- Instance ID: $(ec2-metadata --instance-id | cut -d " " -f 2)

Once deployed, access via SSH tunnel:
ssh -L 8080:localhost:8080 ubuntu@$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
Then browse to: http://localhost:8080
EOF
chown ubuntu:ubuntu /home/ubuntu/deployment-instructions.txt

# Create infrastructure ready marker
touch /home/ubuntu/infrastructure-ready
chown ubuntu:ubuntu /home/ubuntu/infrastructure-ready

echo "Infrastructure setup complete! Instance is ready for application deployment."
echo "See /home/ubuntu/deployment-instructions.txt for next steps."