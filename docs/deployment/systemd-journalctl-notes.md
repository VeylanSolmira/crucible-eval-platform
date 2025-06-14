# Systemd and Journalctl Notes

## 1. Systemctl - Future Setup

Yes, we should add systemctl commands to manage the service. Key commands to add:

```bash
# In SSH tunnel helper section, add service management commands:
cat >> /home/ubuntu/tunnel-help.txt <<EOF

Service Management:
sudo systemctl status crucible-platform    # Check service status
sudo systemctl restart crucible-platform   # Restart the service
sudo systemctl stop crucible-platform      # Stop the service
sudo systemctl start crucible-platform     # Start the service
sudo journalctl -u crucible-platform -f    # View logs (real-time)
EOF
```

## 2. Journalctl - Quick Overview

**journalctl** is systemd's unified logging system that collects and manages all system logs.

### Key Benefits:
- **Centralized**: All logs in one place (kernel, services, applications)
- **Structured**: Logs include metadata (timestamp, priority, service name)
- **Persistent**: Survives reboots (configurable)
- **Queryable**: Powerful filtering and search capabilities

### Common Commands:
```bash
# View logs for our service
journalctl -u crucible-platform

# Follow logs in real-time (like tail -f)
journalctl -u crucible-platform -f

# Show only errors
journalctl -u crucible-platform -p err

# View logs since last boot
journalctl -u crucible-platform -b

# View logs from last hour
journalctl -u crucible-platform --since "1 hour ago"

# Export logs
journalctl -u crucible-platform > crucible.log
```

### Why It's Better Than Text Files:
- Automatic rotation and size limits
- Binary format prevents tampering
- Rich metadata for debugging
- Integrated with systemd service lifecycle

## 3. Avoiding Inline Systemd Files

Yes, we can avoid inline systemd files! Here are better approaches:

### Option A: Separate Service File (Recommended)
```bash
# Create templates/crucible-platform.service
# Then in userdata:
aws s3 cp s3://${deployment_bucket}/crucible-platform.service /etc/systemd/system/
# OR
curl -o /etc/systemd/system/crucible-platform.service https://raw.githubusercontent.com/${github_repo}/${github_branch}/deployment/crucible-platform.service
```

### Option B: Package It Properly
Include the service file in your deployment package:
```bash
# In your deployment package:
deployment/
├── crucible-platform.service
├── install.sh
└── config/

# In userdata:
cp /home/ubuntu/crucible/deployment/crucible-platform.service /etc/systemd/system/
```

### Option C: Use Configuration Management
For production, use proper tools:
- **Ansible**: Deploy service files as part of playbook
- **Cloud-init**: Use write_files directive
- **Packer**: Bake service file into AMI

### Example Refactored Approach:

1. Create `deployment/systemd/crucible-platform.service`:
```ini
[Unit]
Description=Crucible Evaluation Platform
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/crucible
EnvironmentFile=/etc/crucible/platform.env
ExecStart=/home/ubuntu/crucible/venv/bin/python /home/ubuntu/crucible/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. Create `deployment/systemd/platform.env`:
```bash
PATH=/home/ubuntu/crucible/venv/bin:/usr/bin:/usr/local/bin
PYTHONPATH=/home/ubuntu/crucible
CRUCIBLE_PORT=8080
CRUCIBLE_LOG_LEVEL=INFO
```

3. Update userdata to copy files:
```bash
# Copy systemd files
cp /home/ubuntu/crucible/deployment/systemd/crucible-platform.service /etc/systemd/system/
mkdir -p /etc/crucible
cp /home/ubuntu/crucible/deployment/systemd/platform.env /etc/crucible/
```

This approach is:
- **Cleaner**: Service definition lives with code
- **Versionable**: Changes tracked in git
- **Testable**: Can validate service file syntax
- **Reusable**: Same file for different deployment methods