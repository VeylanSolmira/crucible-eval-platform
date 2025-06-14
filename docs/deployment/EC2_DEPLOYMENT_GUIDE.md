# EC2 Deployment Guide for Crucible Platform

## Overview

This guide covers deploying the Crucible platform to AWS EC2 with:
- Automatic startup via systemd
- SSH tunneling for secure access
- Multiple deployment methods for code
- gVisor container isolation

## Deployment Methods

### Method 1: GitHub Deployment (Simple)

**Best for**: Public repositories or development environments

```bash
# In terraform directory
terraform apply -var="github_repo=https://github.com/yourusername/crucible-platform.git"
```

**Pros**:
- Simple setup
- Easy updates with git pull
- Good for open source

**Cons**:
- Requires public repo or deploy keys
- Source code visible in repo

### Method 2: S3 Deployment (Secure)

**Best for**: Private code, production environments

```bash
# Package your code
cd /path/to/crucible-platform
tar -czf crucible-platform.tar.gz --exclude='.git' --exclude='*.pyc' --exclude='__pycache__' .

# Upload to S3
aws s3 cp crucible-platform.tar.gz s3://your-deployment-bucket/

# Deploy
terraform apply \
  -var="deployment_method=s3" \
  -var="deployment_bucket=your-deployment-bucket" \
  -var="deployment_key=crucible-platform.tar.gz"
```

**Pros**:
- Code stays private
- Versioned deployments
- IAM-based access control

**Cons**:
- More setup required
- Need S3 bucket

### Method 3: Docker Image (Most Secure)

**Best for**: Immutable deployments, CI/CD pipelines

```dockerfile
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install -e .
CMD ["python", "app.py", "--port", "8080"]
```

Push to ECR and deploy via userdata.

## SSH Tunneling

### Basic Setup

```bash
# Single port tunnel
ssh -L 8080:localhost:8080 ubuntu@<ec2-ip>

# Multiple ports
ssh -L 8080:localhost:8080 -L 9090:localhost:9090 ubuntu@<ec2-ip>

# Keep alive
ssh -L 8080:localhost:8080 -o ServerAliveInterval=60 ubuntu@<ec2-ip>
```

### Access Services

- Platform: http://localhost:8080
- Monitoring: http://localhost:9090 (if configured)

### Make it Permanent

Add to `~/.ssh/config`:

```
Host crucible
    HostName <ec2-ip>
    User ubuntu
    LocalForward 8080 localhost:8080
    LocalForward 9090 localhost:9090
    ServerAliveInterval 60
```

Then just: `ssh crucible`

## Security Considerations

### Network Security

1. **SSH Access**: Restricted to your IP only
2. **Web Access**: Through SSH tunnel only
3. **Outbound**: Full access for package installation

### Code Security

1. **S3 Deployment**:
   - Use IAM roles, not keys
   - Enable S3 bucket encryption
   - Use versioning for rollback

2. **GitHub Deployment**:
   - Use deploy keys for private repos
   - Store keys in AWS Systems Manager Parameter Store
   - Never commit secrets

3. **Updates**:
   ```bash
   ssh ubuntu@<ec2-ip>
   sudo update-crucible  # For git repos
   sudo update-crucible s3://bucket/new-version.tar.gz  # For S3
   ```

## Systemd Integration

The platform runs as a systemd service:

```bash
# Check status
sudo systemctl status crucible-platform

# View logs
sudo journalctl -u crucible-platform -f

# Restart
sudo systemctl restart crucible-platform

# Stop/Start
sudo systemctl stop crucible-platform
sudo systemctl start crucible-platform
```

## Monitoring

### Built-in Commands

```bash
# Quick status check
check-crucible

# Full logs
journalctl -u crucible-platform -n 100

# Follow logs
journalctl -u crucible-platform -f
```

### Health Checks

```bash
# From local machine (through tunnel)
curl http://localhost:8080/health

# From EC2 instance
curl http://localhost:8080/health
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
journalctl -u crucible-platform -n 50

# Check Python environment
/home/ubuntu/crucible/venv/bin/python --version

# Check Docker
docker run hello-world
docker run --runtime=runsc hello-world  # Test gVisor
```

### Permission Issues

```bash
# Fix ownership
sudo chown -R ubuntu:ubuntu /home/ubuntu/crucible

# Check service user
sudo -u ubuntu /home/ubuntu/crucible/venv/bin/python app.py --help
```

### Update Issues

```bash
# Manual update
cd /home/ubuntu/crucible
sudo systemctl stop crucible-platform
git pull  # or extract new tarball
./venv/bin/pip install -r requirements.txt
sudo systemctl start crucible-platform
```

## Best Practices

1. **Use SSH tunnels** instead of opening ports
2. **Enable CloudWatch** for centralized logging
3. **Set up alerts** for service failures
4. **Regular updates** for security patches
5. **Backup your data** in /home/ubuntu/crucible/storage

## Cost Optimization

- Use t2.micro for development (free tier)
- Stop instances when not in use
- Use spot instances for testing
- Consider Lambda for light workloads

## Next Steps

1. Set up CloudWatch logging
2. Configure automated backups
3. Implement auto-scaling
4. Add monitoring dashboards
5. Set up CI/CD pipeline