# EC2 Deployment Guide

This guide walks through deploying the Crucible platform to AWS EC2 with:
- Automatic startup via systemd
- Secure SSH tunneling for access
- Multiple deployment methods (GitHub/S3)
- gVisor container isolation

## Prerequisites

1. **AWS Account** with free tier eligibility
2. **AWS CLI** installed and configured
3. **OpenTofu/Terraform** installed (`brew install opentofu` or `brew install terraform`)
4. **SSH key pair** for EC2 access

## Quick Start

### 1. Configure AWS CLI

```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: us-east-1
# Default output format: json
```

### 2. Configure Variables

```bash
cd infrastructure/terraform

# Copy example variables
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
vim terraform.tfvars
# Set:
# - allowed_ssh_ip (your IP from: curl ifconfig.me)
# - ssh_public_key (from: cat ~/.ssh/id_ed25519.pub)
# - deployment method (github_repo or deployment_bucket)
```

### 3. Deploy Infrastructure

```bash
# Initialize
tofu init  # or terraform init

# Review the plan
tofu plan

# Deploy
tofu apply
```

### 4. Access the Platform

The platform runs automatically via systemd. Access it through SSH tunnel:

```bash
# Get SSH tunnel command from output
tofu output ssh_tunnel_command

# Or manually:
ssh -L 8080:localhost:8080 ubuntu@<instance-ip>

# Then access:
open http://localhost:8080
```

### 5. Monitor Setup Progress

The instance automatically installs Docker, gVisor, Python, and starts the platform:

```bash
# Get the IP from OpenTofu output
tofu output eval_server_public_ip

# SSH to the server
ssh ubuntu@<IP_ADDRESS>

# Check if setup is complete
ls ~/setup-complete
```

### 4. Deploy the Platform

```bash
# SSH to the server
ssh ubuntu@$(tofu output -raw eval_server_public_ip)

# Clone your repository
git clone <your-repo-url> crucible
cd crucible

# Test gVisor is working
docker run --rm --runtime=runsc alpine echo "gVisor works!"

# Run the platform (from evolution examples)
python src/platform/extreme_mvp_gvisor.py
```

### 5. Access the Platform

Open in your browser:
```
http://<EC2_PUBLIC_IP>:8000
```

## Cost Considerations

**Free Tier Eligible:**
- t2.micro: 750 hours/month (enough for 24/7 operation)
- 30GB EBS storage
- 15GB data transfer

**Estimated Cost:** $0/month if within free tier limits

**After Free Tier:** ~$10-15/month for t2.micro

## Security Notes

### Current Setup (Development)
- SSH open to all IPs (0.0.0.0/0)
- Platform port 8000 open to all
- Suitable for testing only

### Production Recommendations
1. Restrict SSH to your IP:
   ```hcl
   cidr_blocks = ["YOUR_IP/32"]
   ```

2. Use Application Load Balancer with HTTPS

3. Move to private subnet with bastion host

4. Enable CloudWatch monitoring

## Testing gVisor

Once connected to the EC2 instance:

```bash
# Verify gVisor is installed
docker run --rm --runtime=runsc alpine uname -a
# Should show: Linux ... 4.4.0 (gVisor's kernel version)

# Run security tests
cd ~/crucible
python extreme_mvp_gvisor.py --runtime=runsc

# The platform should report:
# "Platform is PRODUCTION SAFE (4/4 requirements)"
```

## Troubleshooting

### SSH Connection Refused
- Check security group allows port 22
- Verify instance is running: `aws ec2 describe-instances`

### Docker Permission Denied
```bash
# Logout and login to refresh groups
exit
ssh ubuntu@<IP>
```

### gVisor Not Found
```bash
# Manually install gVisor
curl -fsSL https://gvisor.dev/archive.key | sudo apt-key add -
sudo add-apt-repository "deb https://storage.googleapis.com/gvisor/releases release main"
sudo apt-get update && sudo apt-get install -y runsc
sudo runsc install
sudo systemctl restart docker
```

## Cleanup

To avoid charges:

```bash
# Destroy all resources
tofu destroy
```

## Next Steps

1. **Run Full Test Suite** - Verify all 4/4 requirements
2. **Test Adversarial Code** - Try some "dangerous" Python
3. **Monitor Performance** - Check gVisor overhead
4. **Document Results** - Update your findings

## Alternative: Spot Instances

For even cheaper testing (90% discount but can be terminated):

```hcl
# In ec2.tf, add to aws_instance:
instance_market_options {
  market_type = "spot"
  spot_options {
    max_price = "0.01"  # Max $0.01/hour
  }
}
```