# VPC Architecture Design

## Overview

This document describes the Virtual Private Cloud (VPC) architecture for the Crucible Platform, including network topology, security considerations, and cost optimization strategies.

## Network Architecture

### VPC CIDR Block
- **Primary CIDR**: 10.0.0.0/16 (65,536 IPs)
- **Design Philosophy**: Large enough for future growth, standard private IP range

### Subnet Design

We follow AWS best practices with public and private subnets across multiple Availability Zones:

```
VPC: 10.0.0.0/16
├── Public Subnets (Internet-facing resources)
│   ├── 10.0.0.0/20   (AZ-1: 4,096 IPs)
│   └── 10.0.16.0/20  (AZ-2: 4,096 IPs)
├── Private Subnets (Internal resources)
│   ├── 10.0.32.0/20  (AZ-1: 4,096 IPs)
│   └── 10.0.48.0/20  (AZ-2: 4,096 IPs)
└── Reserved for Future Use
    ├── 10.0.64.0/18  (16,384 IPs)
    └── 10.0.128.0/17 (32,768 IPs)
```

### Subnet Purposes

**Public Subnets:**
- NAT Gateways/Instances
- Application Load Balancers
- Bastion hosts
- Public-facing services

**Private Subnets:**
- Kubernetes nodes
- RDS databases
- ElastiCache clusters
- Application servers
- Container workloads

## Cost Optimization Strategies

### Current Configuration (Development/Learning)

To minimize costs during development, we've disabled expensive managed services:

| Resource | Production Cost | Dev Alternative | Savings |
|----------|-----------------|-----------------|---------|
| NAT Gateway (2x) | ~$90/month | NAT Instance or Public Subnets | $90/month |
| ECR VPC Endpoints (2x) | ~$14.40/month | Use NAT for ECR pulls | $14.40/month |
| **Total Savings** | | | **~$104.40/month** |

### NAT Options Comparison

#### Option 1: NAT Gateway (Production)
```hcl
# Fully managed, highly available
resource "aws_nat_gateway" "main" {
  count         = 2  # One per AZ
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
}
```

**Pros:**
- Managed service (no maintenance)
- Highly available within AZ
- Scales to 45 Gbps
- No single point of failure

**Cons:**
- $45/month per gateway
- No customization options

#### Option 2: NAT Instance (Development)
```hcl
# Self-managed EC2 instance
resource "aws_instance" "nat_instance" {
  instance_type     = "t3.nano"  # ~$3.80/month
  source_dest_check = false       # Required for NAT
}
```

**Pros:**
- ~90% cheaper than NAT Gateway
- Full control over instance
- Can add security tools (IDS/IPS)
- Can use for other purposes (VPN, proxy)

**Cons:**
- Manual patching required
- Single point of failure
- Limited to instance bandwidth
- Requires security group management

#### Option 3: Public Subnets Only (Testing)
For maximum cost savings during initial testing:
- Place all resources in public subnets
- Use security groups for protection
- No NAT costs at all

**Security considerations:**
- All instances need public IPs
- Increased attack surface
- Not recommended for sensitive workloads

## Security Architecture

### Network Security Layers

1. **Internet Gateway**
   - Single entry/exit point for VPC
   - Stateless routing

2. **Security Groups** (Stateful)
   - Instance-level firewalls
   - Allow rules only
   - Applied to ENIs

3. **Network ACLs** (Stateless)
   - Subnet-level firewalls
   - Allow and deny rules
   - Default allows all

4. **Route Tables**
   - Control traffic flow between subnets
   - Separate tables for public/private

### NAT Instance Security

When using NAT instance for cost savings:

```bash
# User data script for NAT instance
#!/bin/bash
# Enable IP forwarding
echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
sysctl -p

# Configure iptables for NAT
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
iptables -F FORWARD

# Security hardening
# Disable source/destination check (required for NAT)
# Limit SSH access to specific IPs
# Enable CloudWatch monitoring
# Regular patching via Systems Manager
```

### VPC Endpoints

For production environments, VPC endpoints reduce costs and improve security:

```hcl
# S3 Gateway Endpoint (Free)
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.${var.aws_region}.s3"
}

# ECR Interface Endpoints (Paid - $7.20/month each)
# Enable for private ECR access without NAT
```

## Kubernetes Integration

The VPC is designed to support Kubernetes deployments:

### Subnet Tagging
```hcl
# Public subnets - for Load Balancers
tags = {
  "kubernetes.io/role/elb" = "1"
}

# Private subnets - for Internal Load Balancers
tags = {
  "kubernetes.io/role/internal-elb" = "1"
}
```

### IP Address Planning
- Reserve /24 blocks for large Kubernetes clusters
- Consider pod networking requirements (CNI plugin)
- Plan for service CIDR ranges

## Migration Path

### Phase 1: Development (Current)
- Single VPC with public subnets
- NAT instance for cost savings
- Basic security groups

### Phase 2: Staging
- Enable private subnets
- Add VPC endpoints for AWS services
- Implement network ACLs

### Phase 3: Production
- Multi-AZ NAT Gateways
- VPC Flow Logs
- AWS Network Firewall
- Transit Gateway for multi-VPC

## Terraform Configuration

### Enabling Cost-Optimized Mode
```hcl
# terraform.tfvars
use_nat_instance = true  # Use cheap NAT instance
```

### Enabling Production Mode
```hcl
# terraform.tfvars
use_nat_instance = false  # Use NAT Gateways

# Uncomment in vpc.tf:
# - NAT Gateway resources
# - ECR VPC Endpoints
# - Update route tables
```

## Monitoring and Troubleshooting

### Key Metrics
- NAT instance CPU/Network
- VPC Flow Logs (when enabled)
- Route table associations
- Security group rules

### Common Issues
1. **No internet from private subnet**
   - Check NAT instance/gateway status
   - Verify route tables
   - Check security groups

2. **Can't pull ECR images**
   - Enable ECR endpoints or
   - Ensure NAT is working
   - Check IAM permissions

3. **High NAT costs**
   - Review data transfer patterns
   - Consider VPC endpoints
   - Implement caching strategies

## Cost Estimation

### Minimal Setup (Dev/Learning)
- VPC: $0
- Subnets: $0
- IGW: $0
- NAT Instance (t3.nano): ~$3.80/month
- **Total: ~$3.80/month**

### Production Setup
- VPC: $0
- Subnets: $0
- IGW: $0
- NAT Gateways (2x): ~$90/month
- VPC Endpoints: ~$14.40/month
- VPC Flow Logs: ~$5/month
- **Total: ~$109.40/month**

### Data Transfer Costs
- NAT Gateway: $0.045/GB
- NAT Instance: Regular EC2 data transfer rates
- VPC Endpoints: No data transfer charges for same-region

## Best Practices

1. **Start simple** - Use public subnets for initial testing
2. **Plan IP space** - Reserve large blocks for future growth
3. **Use tags** - Consistent tagging for cost allocation
4. **Monitor costs** - Set up billing alerts
5. **Document changes** - Keep architecture diagrams updated
6. **Security first** - Default deny, explicit allow
7. **Automate** - Use Infrastructure as Code (Terraform)