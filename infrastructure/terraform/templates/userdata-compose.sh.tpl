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

# Install AWS CLI, jq, cloud-utils, and web server tools
apt-get install -y awscli jq cloud-utils nginx

# Create application directory
mkdir -p /home/ubuntu/crucible/data
chown -R ubuntu:ubuntu /home/ubuntu/crucible

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
   - Backend API: http://localhost:8080 (via SSH tunnel)
   - Frontend UI: http://localhost:3000 (via SSH tunnel)
   
SSH tunnel command:
ssh -L 8080:localhost:8080 -L 3000:localhost:3000 ubuntu@$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

Instance Details:
- Instance ID: $INSTANCE_ID
- Deployment Color: ${deployment_color}
- ECR Repository: ${ecr_repository_url}
EOF
chown ubuntu:ubuntu /home/ubuntu/deployment-instructions.txt

# Configure Nginx (if domain is configured)
if [ -n "${domain_name}" ]; then
    echo "Configuring Nginx for ${domain_name}..."
    
    # Remove default site
    rm -f /etc/nginx/sites-enabled/default
    
    # Check if SSL certificates are available in SSM Parameter Store FIRST
    SSL_AVAILABLE=false
    # Get region from availability zone (remove last character)
    AZ=$(ec2metadata --availability-zone)
    REGION=$${AZ%?}  # Remove last character (the AZ letter)
    
    if aws ssm get-parameter --name "/${project_name}/ssl/certificate" --region $REGION >/dev/null 2>&1; then
        echo "SSL certificates found in Parameter Store, installing..."
        SSL_AVAILABLE=true
        
        # Create SSL directory
        mkdir -p /etc/nginx/ssl
        
        # Get certificate
        aws ssm get-parameter --name "/${project_name}/ssl/certificate" \
            --with-decryption --region $REGION \
            --query 'Parameter.Value' --output text > /etc/nginx/ssl/${domain_name}.crt
        
        # Get private key
        aws ssm get-parameter --name "/${project_name}/ssl/private_key" \
            --with-decryption --region $REGION \
            --query 'Parameter.Value' --output text > /etc/nginx/ssl/${domain_name}.key
        
        # Get issuer chain
        aws ssm get-parameter --name "/${project_name}/ssl/issuer_pem" \
            --with-decryption --region $REGION \
            --query 'Parameter.Value' --output text > /etc/nginx/ssl/${domain_name}.chain.crt
        
        # Create full chain
        cat /etc/nginx/ssl/${domain_name}.crt /etc/nginx/ssl/${domain_name}.chain.crt > /etc/nginx/ssl/${domain_name}.fullchain.crt
        
        # Set proper permissions
        chmod 600 /etc/nginx/ssl/*
        chown root:root /etc/nginx/ssl/*
        
        echo "SSL certificates installed successfully!"
    else
        echo "ERROR: No SSL certificates found in Parameter Store"
        echo "SSL certificates are required for secure operation"
        echo "Ensure 'create_route53_zone = true' in Terraform and ACME certificates are created"
        echo "Nginx setup will be skipped to prevent insecure configuration"
        exit 1  # Fail the userdata script
    fi
    
    # Create Nginx configuration
    cat > /etc/nginx/sites-available/crucible <<'EOFNGINX'
${nginx_config}
EOFNGINX
    
    # Update the configuration to use SSL certificates
    sed -i "s|# ssl_certificate .*|ssl_certificate /etc/nginx/ssl/${domain_name}.fullchain.crt;|" /etc/nginx/sites-available/crucible
    sed -i "s|# ssl_certificate_key .*|ssl_certificate_key /etc/nginx/ssl/${domain_name}.key;|" /etc/nginx/sites-available/crucible
    
    # Create rate limiting configuration
    cat > /etc/nginx/conf.d/rate-limits.conf <<'EOFLIMITS'
${nginx_rate_limits}
EOFLIMITS
    
    # Enable site
    ln -sf /etc/nginx/sites-available/crucible /etc/nginx/sites-enabled/
    
    # Test configuration
    nginx -t
    
    # Enable and restart Nginx to ensure new config is loaded
    systemctl enable nginx
    systemctl restart nginx
    
    echo "Nginx configured for ${domain_name}"
else
    echo "No domain configured, skipping Nginx setup"
fi

echo "Infrastructure setup complete! Ready for docker-compose deployment."