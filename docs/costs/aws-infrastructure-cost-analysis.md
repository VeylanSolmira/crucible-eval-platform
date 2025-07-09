# AWS Infrastructure Cost Analysis

## Executive Summary

The METR Evaluation Platform uses a blue-green deployment strategy with duplicated resources for zero-downtime deployments. The current monthly estimated cost is **$34.44/month** for the full setup, with potential to reduce to **$20-25/month** through optimization.

## Detailed Cost Breakdown

### 1. Compute Resources (EC2)

#### Main Platform Instances
- **Configuration**: 2x t2.micro instances (blue & green)
- **Storage**: 30 GB gp3 EBS volumes each
- **Monthly Cost**:
  - EC2 instances: 2 × $8.47 = **$16.94**
  - EBS volumes: 2 × 30GB × $0.08/GB = **$4.80**
  - **Subtotal**: **$21.74**

#### GPU Instances (Optional)
- **Status**: Disabled by default (`gpu_instances_enabled = false`)
- **Available Types**:
  - Budget (g3s.xlarge): $0.225/hour (~$162/month)
  - Small (g4dn.xlarge): $0.526/hour (~$379/month)
  - Medium (g4dn.2xlarge): $1.052/hour (~$758/month)
  - Large (g5.2xlarge): $2.012/hour (~$1,449/month)
- **Current Cost**: **$0** (disabled)

### 2. Network Resources

#### Elastic IPs
- **Configuration**: 2x Elastic IPs (blue & green)
- **Monthly Cost**: 2 × $3.60 = **$7.20**

#### Route 53 DNS
- **Resources**:
  - 2 hosted zones (veylan.dev, crucible.veylan.dev)
  - 1 HTTPS health check
  - DNS queries
- **Monthly Cost**:
  - Hosted zones: 2 × $0.50 = **$1.00**
  - Health check: **$0.50**
  - DNS queries: ~**$0.10** (estimated)
  - **Subtotal**: **$1.60**

### 3. Storage Services

#### S3 Buckets
- **Buckets**:
  - `dev-crucible-deployment-{account-id}` (deployment artifacts)
  - `dev-crucible-results-{account-id}` (evaluation outputs)
- **Features**: Versioning, encryption, lifecycle policies
- **Monthly Cost**: ~**$0.50** (minimal usage)

#### ECR Repository
- **Configuration**: 
  - 1 repository for all container images
  - Lifecycle: Keep last 10 images, remove untagged after 7 days
- **Monthly Cost**: ~**$1.00** (10 images × ~500MB each)

### 4. Monitoring & Management

#### CloudWatch
- **Resources**:
  - 2 log groups (7-day retention)
  - 8 configured alarms
  - 1 custom dashboard
  - Custom metrics (OOM, restarts, errors)
- **Monthly Cost**: ~**$2.00**

#### Systems Manager (SSM)
- **Usage**: Parameter store for configuration
- **Monthly Cost**: **Free** (standard parameters)

#### Secrets Manager
- **Secrets**: 1 (database password)
- **Monthly Cost**: **$0.40**

#### SNS
- **Usage**: Alert notifications
- **Monthly Cost**: **Free** (within email notification free tier)

### 5. Security & IAM

All IAM resources (roles, policies, profiles) are **free**.

## Total Monthly Costs

| Category | Resource | Monthly Cost |
|----------|----------|-------------|
| Compute | 2x t2.micro EC2 instances | $16.94 |
| Storage | 2x 30GB EBS volumes | $4.80 |
| Network | 2x Elastic IPs | $7.20 |
| DNS | Route 53 (zones + health check) | $1.60 |
| Object Storage | S3 buckets | $0.50 |
| Container Registry | ECR repository | $1.00 |
| Monitoring | CloudWatch | $2.00 |
| Secrets | Secrets Manager | $0.40 |
| **TOTAL** | | **$34.44** |

## Blue-Green Deployment Cost Impact

The blue-green deployment strategy adds approximately **$14.47/month**:
- Extra EC2 instance: +$8.47
- Extra EBS volume: +$2.40
- Extra Elastic IP: +$3.60

## Cost Optimization Strategies

### 1. Development Environment Optimization (~$15/month savings)

**Single Color Deployment**
```hcl
# terraform.tfvars
enabled_deployment_colors = ["green"]  # Disable blue
active_deployment_color = "green"
```

This eliminates:
- 1 EC2 instance: -$8.47
- 1 EBS volume: -$2.40
- 1 Elastic IP: -$3.60

### 2. Instance Optimization (~$10/month savings)

**Use Spot Instances**
- t2.micro spot: ~$0.003/hour vs $0.0116/hour on-demand
- 70% cost reduction possible
- Suitable for development/testing environments

### 3. Storage Optimization (~$2/month savings)

**Reduce EBS Volume Size**
```hcl
# ec2.tf
root_block_device {
  volume_size = 20  # Reduced from 30GB
}
```
- Saves $0.80/month per instance

**Optimize CloudWatch Logs**
```hcl
# cloudwatch.tf
retention_in_days = 3  # Reduced from 7 days
```

### 4. Network Optimization (~$4/month savings)

**Dynamic Elastic IP Allocation**
- Release unused Elastic IPs
- Allocate only during active deployments
- Use instance public IPs for development

### 5. DNS Optimization (~$1/month savings)

**Simplify Route53 Setup**
- Use only subdomain zone (remove root zone)
- Use external monitoring instead of Route53 health checks
- Consider using Cloudflare for DNS (free tier)

## Recommended Configurations

### Development/Testing Environment
```hcl
# Optimized for cost (~$15-20/month)
enabled_deployment_colors = ["green"]
instance_type = "t2.micro"
create_route53_zone = false  # Use external DNS
```

### Production Environment
```hcl
# Optimized for reliability (~$30-35/month)
enabled_deployment_colors = ["blue", "green"]
instance_type = "t3.small"  # Better baseline performance
create_route53_zone = true
```

### Minimal Testing Environment
```hcl
# Absolute minimum (~$10/month)
enabled_deployment_colors = ["green"]
instance_type = "t2.micro"
create_route53_zone = false
# Stop instance when not in use
```

## Cost Scaling Factors

### Data Growth Impact
- **S3 Storage**: $0.023/GB/month
- **EBS Snapshots**: $0.05/GB/month
- **Data Transfer**: $0.09/GB (out to internet)

### Traffic Growth Impact
- **CloudWatch Logs**: $0.50/GB ingested
- **Route53 Queries**: $0.40/million queries
- **Data Transfer**: First 1GB free, then $0.09/GB

### Container Image Growth
- **ECR Storage**: $0.10/GB/month
- Mitigated by lifecycle policies

## Free Tier Considerations

### First Year Benefits (if eligible)
- **EC2**: 750 hours/month of t2.micro (covers one instance)
- **EBS**: 30GB of storage
- **S3**: 5GB of standard storage
- **CloudWatch**: 10 custom metrics, 5GB of logs

**Potential first-year savings**: ~$11-15/month

## Cost Monitoring Recommendations

1. **Set up AWS Budget Alerts**
   - Monthly budget: $40
   - Alert at 80% and 100% thresholds

2. **Enable Cost Explorer**
   - Track daily costs by service
   - Identify unexpected charges

3. **Use AWS Cost Anomaly Detection**
   - Automatic alerts for unusual spending

4. **Tag Resources Properly**
   ```hcl
   common_tags = {
     Project = "crucible-platform"
     Environment = "production"
     CostCenter = "engineering"
   }
   ```

## Conclusion

The current infrastructure is well-designed for production use with blue-green deployments. For development and testing, significant savings (40-60%) are possible by:

1. Using single-color deployments
2. Stopping instances when not in use
3. Leveraging spot instances
4. Optimizing storage and monitoring retention

The architecture scales efficiently, with most costs being linear to usage rather than step functions.