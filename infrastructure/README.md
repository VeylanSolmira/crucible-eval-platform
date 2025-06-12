# Infrastructure

This directory contains Infrastructure as Code (IaC) for deploying the Crucible platform.

## Structure

```
infrastructure/
├── terraform/          # AWS infrastructure (OpenTofu/Terraform HCL)
│   ├── main.tf        # Provider configuration
│   ├── variables.tf   # Input variables
│   ├── api.tf         # API Gateway / Lambda
│   ├── queue.tf       # SQS / Event processing
│   ├── ec2.tf         # EC2 instance for gVisor testing
│   └── PROVIDER_COMPATIBILITY.md  # AWS provider version testing
└── kubernetes/        # K8s manifests (future)
```

## Current Components

### EC2 Evaluation Server (`ec2.tf`)
- **Purpose**: Test gVisor runtime on Linux
- **Instance**: t2.micro (free tier eligible)
- **Software**: Docker + gVisor + Python 3.11
- **Security**: Basic security group for SSH + port 8000

## Quick Start

```bash
cd terraform

# If using direnv (recommended)
direnv allow

# Initialize providers
tofu init

# Plan changes
tofu plan

# Apply infrastructure
tofu apply
```

**Note**: We use OpenTofu instead of Terraform. AWS provider versions 5.90+ have compatibility issues - see [terraform/PROVIDER_COMPATIBILITY.md](terraform/PROVIDER_COMPATIBILITY.md) for details.

See [EC2 Deployment Guide](../docs/ec2-deployment-guide.md) for detailed deployment instructions.

## Future Components

### API Gateway + Lambda (`api.tf`)
- RESTful API for evaluation submission
- Validation and queuing logic

### SQS Queue (`queue.tf`)  
- Async job processing
- Dead letter queue for failures

### Kubernetes Cluster
- Production-grade orchestration
- Multi-node evaluation processing

## Cost Management

Current setup is **free tier eligible**:
- 750 hours/month t2.micro
- 30GB EBS storage

To minimize costs:
1. Use `tofu destroy` when not testing
2. Consider spot instances for development
3. Set up billing alerts

## Security Notes

⚠️ **Current setup is for development only**

Production would require:
- VPC with private subnets
- Bastion host for SSH
- Application Load Balancer
- HTTPS/TLS certificates
- IAM roles and policies