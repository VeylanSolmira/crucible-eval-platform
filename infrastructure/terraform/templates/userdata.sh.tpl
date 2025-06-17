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
mkdir -p /home/ubuntu/${project_name}
mkdir -p /home/ubuntu/storage
mkdir -p /var/log/${project_name}
chown -R ubuntu:ubuntu /home/ubuntu/${project_name} /home/ubuntu/storage /var/log/${project_name}

# Configure AWS CLI for ECR
aws configure set default.region $(ec2-metadata --availability-zone | sed 's/placement: //' | sed 's/.$//')

# Create docker login helper script
cat > /usr/local/bin/docker-ecr-login << 'EOFSCRIPT'
#!/bin/bash
REGION=$(ec2-metadata --availability-zone | sed 's/placement: //' | sed 's/.$//')
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $(aws ecr describe-repositories --repository-names ${project_name} --query 'repositories[0].repositoryUri' --output text | cut -d/ -f1)
EOFSCRIPT
chmod +x /usr/local/bin/docker-ecr-login

# Register this instance as ready for deployment
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
aws ssm put-parameter \
    --name "/${project_name}/instances/$INSTANCE_ID/status" \
    --value "ready" \
    --type "String" \
    --overwrite 2>/dev/null || true

# Store deployment bucket name if provided
if [ -n "${deployment_bucket}" ]; then
    aws ssm put-parameter \
        --name "/${project_name}/instances/$INSTANCE_ID/deployment-bucket" \
        --value "${deployment_bucket}" \
        --type "String" \
        --overwrite 2>/dev/null || true
fi

# Copy systemd service file (with ECR URL already substituted)
cat > /etc/systemd/system/crucible-docker.service <<'EOFSYSTEMD'
${docker_service_content}
EOFSYSTEMD

# Enable but don't start the service (no image yet)
systemctl daemon-reload
systemctl enable crucible-docker.service

# Create deployment instructions
cat > /home/ubuntu/deployment-instructions.txt <<EOF
=== Crucible Platform Docker Deployment Instructions ===

This EC2 instance is ready for Docker deployment but has NO CONTAINER IMAGE.
Following the Kubernetes pattern: infrastructure is ready, container deployment is separate.

To deploy the application:

1. From GitHub Actions (Recommended):
   - Go to: https://github.com/${github_repo}/actions
   - Click "Deploy Docker Container" workflow
   - Click "Run workflow" button
   - Select branch: ${github_branch}

2. From GitHub CLI:
   gh workflow run deploy-docker.yml

3. Check deployment status:
   # Service status
   systemctl status crucible-docker
   
   # Container logs
   docker logs ${project_name}
   journalctl -u ${project_name}-docker -f

Instance Status:
- Infrastructure: ✅ Ready (Docker + gVisor installed)
- Container: ⏳ Awaiting deployment
- ECR Repository: ${ecr_repository_url}
- Instance ID: $(curl -s http://169.254.169.254/latest/meta-data/instance-id)

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