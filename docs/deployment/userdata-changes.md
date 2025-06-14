# UserData Changes - Original vs New Template

## Summary of Changes

The new userdata template builds upon the original with these key additions:

1. **Logging** - Added output redirection to `/var/log/userdata.log`
2. **Additional Tools** - Added `jq` and `awscli` packages
3. **Log Directory** - Created `/var/log/crucible` for application logs
4. **Deployment Methods** - Added GitHub clone and S3 download options
5. **Python Virtual Environment** - Proper venv setup with pip
6. **Package Installation** - Support for requirements.txt and pyproject.toml
7. **Systemd Service** - Auto-start with proper configuration
8. **SSH Tunnel Helper** - Created tunnel-help.txt with instructions

## Detailed Comparison

### 1. Logging Enhancement
```bash
# NEW: Added at the beginning
exec > >(tee -a /var/log/userdata.log)
exec 2>&1
```

### 2. Additional Packages
```bash
# ORIGINAL:
apt-get install -y git

# NEW:
apt-get install -y git jq awscli
```

### 3. Directory Structure
```bash
# NEW: Added log directory
mkdir -p /var/log/crucible
chown ubuntu:ubuntu /var/log/crucible
```

### 4. Code Deployment (Major Addition)
```bash
# NEW: Flexible deployment from GitHub or S3
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
```

### 5. Python Environment Setup (Major Addition)
```bash
# NEW: Only if code was deployed
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
```

### 6. Systemd Service (Major Addition)
```bash
# NEW: Complete systemd service configuration
cat > /etc/systemd/system/crucible-platform.service <<'EOF'
[Unit]
Description=Crucible Evaluation Platform
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/crucible
Environment="PATH=/home/ubuntu/crucible/venv/bin:/usr/bin:/usr/local/bin"
Environment="PYTHONPATH=/home/ubuntu/crucible"

ExecStartPre=/usr/bin/docker --version
ExecStartPre=/home/ubuntu/crucible/venv/bin/python --version
ExecStart=/home/ubuntu/crucible/venv/bin/python /home/ubuntu/crucible/app.py --port 8080

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=crucible-platform

# Resource limits
MemoryLimit=2G
CPUQuota=80%

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
systemctl daemon-reload
systemctl enable crucible-platform
systemctl start crucible-platform
```

### 7. SSH Tunnel Helper (New)
```bash
# NEW: Helper instructions for users
cat > /home/ubuntu/tunnel-help.txt <<EOF
SSH Tunnel Instructions:
ssh -L 8080:localhost:8080 ubuntu@$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
Then access: http://localhost:8080
EOF
chown ubuntu:ubuntu /home/ubuntu/tunnel-help.txt
```

## Key Improvements

1. **Automatic Deployment** - No manual git clone needed
2. **Service Management** - Platform starts automatically on boot
3. **Proper Python Environment** - Isolated venv with dependencies
4. **Better Logging** - All setup output saved to log file
5. **Resource Limits** - Memory and CPU limits for safety
6. **Security Hardening** - NoNewPrivileges, PrivateTmp
7. **User Convenience** - SSH tunnel instructions readily available

## Backward Compatibility

The new template maintains all original functionality:
- Docker installation ✓
- gVisor setup ✓
- Python 3.11 ✓
- Ubuntu user configuration ✓
- Setup completion marker ✓

The additions are conditional and won't interfere if deployment variables aren't set.