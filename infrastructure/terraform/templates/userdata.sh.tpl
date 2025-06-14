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

# Create directory for the platform
mkdir -p /home/ubuntu/crucible
mkdir -p /var/log/crucible
chown ubuntu:ubuntu /home/ubuntu/crucible
chown ubuntu:ubuntu /var/log/crucible

# Install git and additional tools
apt-get install -y git jq awscli

# Deploy code based on method
cd /home/ubuntu

# Method 1: Clone from GitHub (if repo is provided)
%{ if github_repo != "" ~}
echo "Deploying from GitHub: ${github_repo}"
sudo -u ubuntu git clone -b ${github_branch} ${github_repo} crucible
%{ endif ~}

# Method 2: Download from S3 (if bucket is provided)
%{ if deployment_bucket != "" && deployment_key != "" ~}
echo "Deploying from S3: s3://${deployment_bucket}/${deployment_key}"
aws s3 cp s3://${deployment_bucket}/${deployment_key} /tmp/crucible.tar.gz
sudo -u ubuntu tar -xzf /tmp/crucible.tar.gz -C /home/ubuntu/crucible
rm /tmp/crucible.tar.gz
%{ endif ~}

# Only proceed with setup if code was deployed
if [ -d /home/ubuntu/crucible ] && [ "$(ls -A /home/ubuntu/crucible)" ]; then
    # Setup Python virtual environment
    cd /home/ubuntu/crucible
    sudo -u ubuntu python3.11 -m venv venv
    sudo -u ubuntu ./venv/bin/pip install --upgrade pip

    # Install dependencies
    if [ -f requirements.txt ]; then
        sudo -u ubuntu ./venv/bin/pip install -r requirements.txt
    fi

    # Install package in development mode
    if [ -f pyproject.toml ]; then
        sudo -u ubuntu ./venv/bin/pip install -e .
    fi

    # Copy systemd service file from repository
    if [ -f /home/ubuntu/crucible/infrastructure/systemd/crucible-platform.service ]; then
        cp /home/ubuntu/crucible/infrastructure/systemd/crucible-platform.service /etc/systemd/system/
    else
        echo "ERROR: crucible-platform.service not found in repository" >&2
        exit 1
    fi
    
    # Copy update script if present
    if [ -f /home/ubuntu/crucible/scripts/update-platform.sh ]; then
        cp /home/ubuntu/crucible/scripts/update-platform.sh /home/ubuntu/
        chmod +x /home/ubuntu/update-platform.sh
        chown ubuntu:ubuntu /home/ubuntu/update-platform.sh
    fi
    
    # Create log directory if it doesn't exist
    mkdir -p /var/log/crucible
    chown ubuntu:ubuntu /var/log/crucible

    # Enable and start the service
    systemctl daemon-reload
    systemctl enable crucible-platform
    systemctl start crucible-platform
else
    echo "No code deployed - skipping platform setup"
fi

# Create SSH tunnel helper with service management commands
cat > /home/ubuntu/tunnel-help.txt <<EOF
SSH Tunnel Instructions:
ssh -L 8080:localhost:8080 ubuntu@$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
Then access: http://localhost:8080

Service Management:
sudo systemctl status crucible-platform    # Check service status
sudo systemctl restart crucible-platform   # Restart the service
sudo systemctl stop crucible-platform      # Stop the service
sudo systemctl start crucible-platform     # Start the service
sudo journalctl -u crucible-platform -f    # View logs (real-time)
EOF
chown ubuntu:ubuntu /home/ubuntu/tunnel-help.txt

# Create a marker file to indicate setup is complete
touch /home/ubuntu/setup-complete
chown ubuntu:ubuntu /home/ubuntu/setup-complete