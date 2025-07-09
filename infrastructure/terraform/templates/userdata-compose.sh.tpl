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
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

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

# Install AWS CLI, jq, cloud-utils
apt-get install -y awscli jq cloud-utils

# Create application directory and storage subdirectories
mkdir -p /home/ubuntu/crucible/data/{evaluations,logs,results,events,metadata}
# Set ownership for container access (most containers run as UID 1000)
chown -R 1000:1000 /home/ubuntu/crucible/data
chmod -R 755 /home/ubuntu/crucible/data
# Keep main crucible directory owned by ubuntu
chown ubuntu:ubuntu /home/ubuntu/crucible

# Configure AWS CLI for ECR
AZ=$(ec2metadata --availability-zone)
aws configure set default.region $${AZ%?}

# Create docker login helper script
cat > /usr/local/bin/docker-ecr-login << 'EOFSCRIPT'
#!/bin/bash
AZ=$(ec2metadata --availability-zone)
REGION=$${AZ%?}
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $(aws ecr describe-repositories --repository-names ${project_name} --query 'repositories[0].repositoryUri' --output text | cut -d/ -f1)
EOFSCRIPT
chmod +x /usr/local/bin/docker-ecr-login

# Register this instance as ready
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
aws ssm put-parameter \
    --name "/${project_name}/instances/$INSTANCE_ID/status" \
    --value "ready" \
    --type "String" \
    --overwrite 2>/dev/null || true

# Copy systemd service file
cat > /etc/systemd/system/crucible-compose.service <<'EOFSYSTEMD'
${compose_service_content}
EOFSYSTEMD

# Enable the service (but don't start - no compose file yet)
systemctl daemon-reload
systemctl enable crucible-compose.service

# Create deployment instructions
cat > /home/ubuntu/deployment-instructions.txt <<EOF
=== Crucible Platform Docker Compose Deployment ===

This EC2 instance is ready for Docker Compose deployment.
Infrastructure: Docker + gVisor (no application code on host)

To deploy the application stack:

1. From GitHub Actions (Recommended):
   - Push to main branch (auto-deploys to blue)
   - Or manually run "Deploy Docker Compose Stack" workflow

2. Check deployment:
   cd /home/ubuntu/crucible
   docker-compose ps
   docker-compose logs

3. Access services:
   - Via HTTPS: https://${domain_name} (if domain configured)
   - Via HTTP: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
   - Via SSH tunnel: http://localhost:8000
   
SSH tunnel command (for local development):
ssh -L 8000:localhost:8000 ubuntu@$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

Instance Details:
- Instance ID: $INSTANCE_ID
- Deployment Color: ${deployment_color}
- ECR Repository: ${ecr_repository_url}
EOF
chown ubuntu:ubuntu /home/ubuntu/deployment-instructions.txt

# Setup SSL certificate refresh automation (only if domain is configured)
if [ -n "${domain_name}" ]; then
    echo "Setting up SSL certificate refresh automation..."
    
    # Copy the refresh script
    cat > /usr/local/bin/refresh-ssl-certs.sh <<'EOFSCRIPT'
${ssl_refresh_script}
EOFSCRIPT
    chmod +x /usr/local/bin/refresh-ssl-certs.sh
    
    # Install systemd service
    cat > /etc/systemd/system/ssl-refresh.service <<'EOFSERVICE'
${ssl_refresh_service}
EOFSERVICE
    
    # Install systemd timer  
    cat > /etc/systemd/system/ssl-refresh.timer <<'EOFTIMER'
${ssl_refresh_timer}
EOFTIMER
    
    # Enable and start the timer
    systemctl daemon-reload
    systemctl enable ssl-refresh.timer
    systemctl start ssl-refresh.timer
    
    echo "SSL certificate refresh automation configured successfully!"
    echo "Timer will run immediately and then hourly to manage SSL certificates"
    
    # Create SSL directory for nginx container to mount
    mkdir -p /etc/nginx/ssl
    
    # The timer with OnActiveSec=0 will run the refresh script immediately
else
    echo "No domain configured, skipping SSL certificate setup"
fi

# Install CloudWatch Agent
echo "Installing CloudWatch Agent..."
wget -q https://s3.$REGION.amazonaws.com/amazoncloudwatch-agent-$REGION/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
dpkg -i -E ./amazon-cloudwatch-agent.deb
rm -f ./amazon-cloudwatch-agent.deb

# Configure and start CloudWatch Agent
echo "Configuring CloudWatch Agent..."
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c ssm:/${project_name}/cloudwatch-agent/config

echo "CloudWatch Agent installed and started successfully!"

echo "Infrastructure setup complete! Ready for docker-compose deployment."