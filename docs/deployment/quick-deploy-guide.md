# Quick Deployment Guide with SSH Tunneling

## Prerequisites
- AWS CLI configured
- OpenTofu/Terraform installed
- SSH key pair ready

## Step 1: Deploy Infrastructure

```bash
cd infrastructure/terraform

# Initialize Terraform
tofu init

# Review the plan
tofu plan

# Deploy infrastructure (creates S3 buckets, EC2, etc.)
tofu apply

# Note the outputs
tofu output
```

## Step 2: Deploy Application to S3

```bash
# From project root
chmod +x scripts/deploy-to-s3.sh

# Deploy current code
./scripts/deploy-to-s3.sh

# Or with specific version
VERSION=v1.0.0 ./scripts/deploy-to-s3.sh
```

## Step 3: Verify Deployment

```bash
# Get your EC2 IP
EC2_IP=$(cd infrastructure/terraform && tofu output -raw eval_server_public_ip)

# SSH to check status
ssh ubuntu@$EC2_IP "sudo systemctl status crucible-platform"

# Check logs
ssh ubuntu@$EC2_IP "sudo journalctl -u crucible-platform -n 50"
```

## Step 4: Create SSH Tunnel

```bash
# Create tunnel for secure access
ssh -L 8080:localhost:8080 ubuntu@$EC2_IP

# Keep this terminal open!
```

## Step 5: Access Platform

In a new terminal or browser:
```bash
# Test the connection
curl http://localhost:8080/health

# Open in browser
open http://localhost:8080
```

## Troubleshooting

### Service Not Starting
```bash
# Check userdata logs
ssh ubuntu@$EC2_IP "sudo cat /var/log/userdata.log"

# Restart service
ssh ubuntu@$EC2_IP "sudo systemctl restart crucible-platform"
```

### Can't Connect Through Tunnel
```bash
# Verify service is listening
ssh ubuntu@$EC2_IP "sudo netstat -tlnp | grep 8080"

# Check firewall isn't blocking
ssh ubuntu@$EC2_IP "sudo iptables -L"
```

### S3 Deploy Issues
```bash
# Verify bucket was created
aws s3 ls | grep crucible

# Check IAM permissions
aws sts get-caller-identity
```

## Daily Workflow

1. **Make code changes**
2. **Test locally**: `python app.py`
3. **Deploy to S3**: `./scripts/deploy-to-s3.sh`
4. **Update EC2**: 
   ```bash
   ssh ubuntu@$EC2_IP "cd /home/ubuntu/crucible && \
     aws s3 cp s3://dev-crucible-deployment-*/crucible-platform-latest.tar.gz . && \
     tar -xzf crucible-platform-latest.tar.gz && \
     sudo systemctl restart crucible-platform"
   ```
5. **Test via tunnel**: `curl http://localhost:8080/health`

## Pro Tips

### Create SSH Alias
Add to `~/.ssh/config`:
```
Host crucible
    HostName <your-ec2-ip>
    User ubuntu
    LocalForward 8080 localhost:8080
    ServerAliveInterval 60
```

Then just: `ssh crucible`

### Background Tunnel
```bash
# Run tunnel in background
ssh -f -N -L 8080:localhost:8080 ubuntu@$EC2_IP

# Find and kill when done
ps aux | grep "ssh -f" | grep 8080
```

### Watch Logs Live
```bash
# In separate terminal while testing
ssh ubuntu@$EC2_IP "sudo journalctl -u crucible-platform -f"
```

## Security Checklist

- ✅ Platform only accessible via SSH tunnel
- ✅ S3 bucket encrypted and versioned
- ✅ EC2 security group restricts SSH to your IP
- ✅ No credentials in code (uses IAM roles)
- ✅ Systemd service runs as non-root user

## Next Steps

Once comfortable with this setup:
1. Add automated deployment script
2. Set up monitoring alerts
3. Create staging environment
4. Move to containerized deployment